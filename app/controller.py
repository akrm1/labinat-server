from app.core.Catalog import Catalog
from app.core.Workspace import Workspace

catalog: Catalog = None
workspace: Workspace = None

def init(catalog_config: dict, workspace_config: dict):
    global catalog
    global workspace

    catalog = Catalog(catalog_config=catalog_config)
    workspace = Workspace(workspace_config=workspace_config)

    catalog.path.mkdir(parents=True, exist_ok=True)
    catalog.path.joinpath("factories").mkdir(parents=True, exist_ok=True)
    catalog.path.joinpath("schemas").mkdir(parents=True, exist_ok=True)
    catalog.path.joinpath("templates").mkdir(parents=True, exist_ok=True)
    
    workspace.path.mkdir(parents=True, exist_ok=True)
    workspace.path.joinpath("projects").mkdir(parents=True, exist_ok=True)