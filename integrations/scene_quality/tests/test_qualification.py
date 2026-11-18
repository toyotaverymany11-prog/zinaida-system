import copy
import unittest
from integrations.scene_quality.contracts import Invalid, digest
from integrations.scene_quality.qualification import SCOPES, evaluate, public_cases, validate_bundle, validate_dataset


def controls():
    identity = {'reviewer_id':'fixture-reviewer','model_revision':'simulated-control-v1','route':'offline-unit-fixture'}
    cases = [{'id':str(i), 'source_group':'distinct-original-'+str(i), 'split':'holdout',
        'artifact_sha256':str(i+1)*64, 'labels':{s:('pass' if i<2 else 'reject') for s in SCOPES},
        'label_basis':'Synthetic unit fixture, never a live model qualification'} for i in range(4)]
    dataset = {'cases':cases}
    predictions = [{'case_id':c['id'],'artifact_sha256':c['artifact_sha256'],
        'runner_receipt_sha256':'a'*64,'identity':identity,'decisions':dict(c['labels'])} for c in cases]
    return dataset, predictions, identity


def bundle():
    d,p,i=controls();return {'dataset':d,'predictions':p,'identity':i,'measured_at':1000,
                            'report':evaluate(d,p,i,measured_at=1000)}


class CriticCalibration(unittest.TestCase):
    def test_one_critical_camera_miss_cannot_be_averaged_with_other_successes(self):
        d,p,i=controls();p[2]['decisions']['camera']='pass';r=evaluate(d,p,i,measured_at=1000)
        self.assertNotIn('camera',r['qualified_scopes']);self.assertIn('brand',r['qualified_scopes'])
        self.assertEqual(r['metrics']['camera']['false_accepts'],1)

    def test_denominators_uncertainty_and_abstention_are_reported(self):
        d,p,i=controls();p[2]['decisions']['brand']='abstain';r=evaluate(d,p,i,measured_at=1000)
        x=r['metrics']['brand'];self.assertEqual((x['positive_cases'],x['negative_cases'],x['abstentions']),(2,2,1))
        self.assertGreater(x['false_accept_wilson_upper_95'],.5)

    def test_development_and_holdout_cannot_share_an_original(self):
        d,_,_=controls();d['cases'].append(dict(d['cases'][0],id='variant',split='development',artifact_sha256='b'*64))
        with self.assertRaisesRegex(Invalid,'leak'):validate_dataset(d)

    def test_renaming_same_bytes_does_not_make_an_independent_control(self):
        d,_,_=controls();d['cases'][1]['artifact_sha256']=d['cases'][0]['artifact_sha256']
        with self.assertRaisesRegex(Invalid,'Identical asset'):validate_dataset(d)

    def test_many_variants_of_one_positive_are_insufficient(self):
        d,p,i=controls();d['cases'][1]['source_group']=d['cases'][0]['source_group']
        self.assertEqual(evaluate(d,p,i,measured_at=1000)['qualified_scopes'],[])

    def test_model_does_not_receive_gold_labels_or_group_names(self):
        d,_,_=controls();self.assertTrue(all(set(x)=={'id','artifact_sha256'} for x in public_cases(d)))

    def test_missing_predictions_are_abstentions_not_success(self):
        d,p,i=controls();r=evaluate(d,p[:1],i,measured_at=1000)
        self.assertEqual(r['qualified_scopes'],[])

    def test_wrong_input_or_mixed_model_rejected(self):
        for mode in ['file','model']:
            d,p,i=controls()
            if mode=='file':p[0]['artifact_sha256']='f'*64
            else:p[0]['identity']=dict(i,model_revision='different-model')
            with self.assertRaises(Invalid):evaluate(d,p,i,measured_at=1000)

    def test_a_green_summary_cannot_replace_actual_control_results(self):
        b=bundle();b['predictions'][2]['decisions']['anatomy']='pass'
        with self.assertRaises(Invalid):validate_bundle(b,now=1001)

    def test_expired_future_or_partial_qualification_cannot_open_release(self):
        b=bundle()
        for now in [999,100000]:
            with self.assertRaises(Invalid):validate_bundle(b,now=now)
        b['predictions'][2]['decisions']['anatomy']='pass';b['report']=evaluate(b['dataset'],b['predictions'],b['identity'],measured_at=1000)
        with self.assertRaises(Invalid):validate_bundle(b,now=1001)
        self.assertIn('brand',validate_bundle(b,now=1001,required_scopes=['brand'])['qualified_scopes'])
