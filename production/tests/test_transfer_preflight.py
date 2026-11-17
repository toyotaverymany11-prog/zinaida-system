import unittest
from unittest.mock import patch
from production.qualification.scoped_model_download import transfer_estimate, preflight


class TransferPreflight(unittest.TestCase):
    def test_transfer_keeps_inference_and_cleanup_inside_original_lease(self):
        from production.qualification.bound_pilot_runner import transfer_budget
        from production.core import ProductionError
        self.assertEqual(transfer_budget(3700,1000),1500)
        self.assertEqual(transfer_budget(2000,1000),280)
        with self.assertRaises(ProductionError):transfer_budget(1750,1000)

    def test_sample_must_fit_original_remaining_time_with_overhead(self):
        self.assertFalse(transfer_estimate(64*1024**2,20,40*1024**3,850)['fits'])
        self.assertTrue(transfer_estimate(64*1024**2,.5,40*1024**3,850)['fits'])
        self.assertFalse(transfer_estimate(64*1024**2,.5,40*1024**3,300)['fits'])
        # Real AP-IN measurement: valid under the granted longer lease.
        self.assertTrue(transfer_estimate(67108864,1.212778,39709872236,1500)['fits'])

    def test_untrusted_location_never_opens_connection(self):
        with patch('urllib.request.urlopen') as opener:
            with self.assertRaises(ValueError):
                preflight([{'url':'http://127.0.0.1/private','bytes':100}],100)
            opener.assert_not_called()

    def test_short_sample_is_not_extrapolated_as_success(self):
        with patch('urllib.request.urlopen') as opener:
            opener.return_value.__enter__.return_value.read1.return_value=b''
            with self.assertRaisesRegex(ValueError,'Incomplete'):
                preflight([{'url':'https://us.aws.cdn.hf.co/test','bytes':100}],100)
