from core.Catalog import Catalog
from core.Workspace import Workspace

catalog: Catalog = None
workspace: Workspace = None

def init(catalog_config: dict, workspace_config: dict):
    global catalog
    global workspace

    catalog = Catalog(catalog_config=catalog_config)
    workspace = Workspace(workspace_config=workspace_config)