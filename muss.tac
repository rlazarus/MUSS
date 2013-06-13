from twisted.application import service, internet

from muss.server import WorldFactory

application = service.Application("MUSS")
mussService = internet.TCPServer(9355, WorldFactory())
mussService.setServiceParent(application)
