# بسم الله الرحمن الرحيم
import server
server.init()

catalog = server.controller.catalog
workspace = server.controller.workspace


factory = catalog.get_factory(factory_name="backend-fastapi", version="v1")
print(factory)
workspace.summary(catalog)

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