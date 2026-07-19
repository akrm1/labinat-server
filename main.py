# بسم الله الرحمن الرحيم
import server
server.init()

from base.Spec import Spec
from base.Binding import Binding

schema = {
    "type": "object",
    "properties": {
        "name": {
            "type": ["binding.table", "binding.model"]
        },
        "columns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string"
                    }
                }
            }
        }
    }
}

data = {
    "name": "@block.name",
    "columns": [
        {
            "name": "blue",
            "type": "integer"
        }
    ]
}


spec = Spec(data)

spec.define_binding("pra", "table", [
    Binding(
        binding_object="block",
        type_fetcher=lambda z: 'table',
        object_fetcher=lambda z: 2,
        binder=lambda x, y: f"{x}-{y}"
    )
])
spec.define_binding("tra", "model", [
    Binding(
        binding_object="block",
        type_fetcher=lambda z: 'table',
        object_fetcher=lambda z: 5,
        binder=lambda x, y: f"{x}-{y}"
    )
])

spec.validate(schema)
spec = spec.decode()
print(spec.asjson())

#catalog = server.controller.catalog
#workspace = server.controller.workspace


#factory = catalog.get_factory(factory_name="backend-fastapi", version="v1")

project_id = "b07ac48f-98b7-46c3-bc53-da558a676621"
config = {
    "app": {
        "name": "akrm_website"
    }
}

#project = workspace.create_project(name="my_website", description="My website", config=config)
#project.add_factory(factory)
#project.clone()
#project = workspace.get_project(project_id=project_id, catalog=catalog)
#workspace.delete_project(project_id=project_id)
#project.clone()
#print(project)

#catalog.summary()

#project = workspace.create_project(name="my_website", description="My website")
#print(project)

#projects = workspace.get_all_projects()
#for project in projects:
#    print(project.id, project.name, project.created_at)

#catalog.load_all_factories()

#factory = catalog.get_factory("backend-fastapi")
#print(factory.asjson())


#data = {
#    "name": "users",
#    "columns": [
#        {
#            "name": "blue",
#            "type": "integer"
#        }
#    ]
#}
#
#project = server.workspace.load_project("my_website")
#
#backend_fastapi = project.get_factory("backend-fastapi")
#
#
##backend_fastapi.app.build(project={"id": "my_website"})
#block = server.workspace.load_block("t2", backend_fastapi.frames["table"])
#
#
#block.spec.decode()
#print(server.workspace)

# الحمد لله رب العالمين