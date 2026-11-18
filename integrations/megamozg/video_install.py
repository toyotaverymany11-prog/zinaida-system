"""Install explicitly configured video routes without source-directory access."""
import json
from pathlib import Path
from video_routes import install as install_status
from video_media import install as install_media
from video_producer_service import client


def install(app,config_path):
    config=json.loads(Path(config_path).read_text())
    bindings=config['bindings'];socket=config['socket']
    install_status(app,app['store'],bindings,lambda link:client(socket,link,None,'metadata'))
    install_media(app,app['store'],bindings,lambda link,revision,kind:client(socket,link,revision,kind))
    if config.get('owner_imported_draft_preview') is True:
        from video_owner_preview import install_imported
        install_imported(app,app['store'],bindings,lambda link,artifact_id,kind:client(socket,link,artifact_id,kind))
    if config.get('owner_draft_preview') is True:
        from video_owner_preview import install as install_owner_preview
        install_owner_preview(app,app['store'],bindings,lambda link,revision,kind:client(socket,link,revision,kind))


# Draft routes are installed only by an explicit owner-preview configuration.
