import cherrypy
import json
import urllib

from quads import model as m
from quads.model import Cloud

class MethodHandlerBase(object):
    def __init__(self, model, name, proprty=None):
        self.m = model
        self.name = name
        self.proprty = proprty

    def _get_obj(self, obj):
        q = {self.name: obj}
        obj = self.m.objects(**q).first()
        return obj


@cherrypy.expose
class DocumentMethodHandler(MethodHandlerBase):
    def GET(self, **data):
        args = {}
        if 'cloudonly' in data:
            c = Cloud.objects(cloud=data['cloudonly'])
            if not c:
                cherrypy.response.status = "404 Not Found"
                return json.dumps({'result':
                        'Cloud %s Not Found' % data['cloudonly']})
            else:
                return c.to_json()
        return self.m.objects(**args).to_json()

    # post data comes in **data
    def POST(self, **data):
        # handle force
        force = True if data.get('force', False) == 'True' else False
        if 'force' in data:
            del data['force']

        # make sure post data passed in is ready to pass to mongo engine
        result, data = self.m.prep_data(data)

        # Check if there were data validation errors
        if result:
            result = ['Data validation failed: %s' % ', '.join(result)]
            cherrypy.response.status = "400 Bad Request"
        else:
            # check if object already exists
            obj = self._get_obj(data[self.name])
            if obj and not force:
                result.append('%s %s already exists' % (
                                self.name,
                                data[self.name]))
                cherrypy.response.status = "409 Conflict"
            else:
                # Create/update Operation
                try:
                    # if force and found object do an update
                    if force and obj:
                        # TODO: DEFAULTS OVERWRITE EXISTING VALUES
                        obj.update(**data)
                        result.append('Updated %s %s' % (self.name,
                                                         data[self.name]))
                    # otherwise create it
                    else:
                        obj = self.m(**data).save()
                        cherrypy.response.status = "201 Resource Created"
                        result.append('Created %s %s' % (self.name,
                                                         data[self.name]))
                except Exception, e:
                    # TODO: make sure when this is thrown the output
                    #       points back to here and gives the end user
                    #       enough information to fix the issue
                    cherrypy.response.status = "500 Internal Server Error"
                    result.append('Error: %s' % e)
        print result
        return json.dumps({'result': result})

    def PUT(self, **data):
        # update operations are done through POST
        # using PUT would duplicate most of POST
        return self.POST(**data)

    def DELETE(self, obj_name):
        obj = self._get_obj(obj_name)
        if obj:
            obj.delete()
            result = ['deleted %s %s' % (self.name, obj_name)]
        else:
            cherrypy.response.status = "404 Not Found"
            result = ['%s %s Not Found' % (self.name, obj_name)]
        return json.dumps({'result': result})

@cherrypy.expose
class PropertyMethodHandler(MethodHandlerBase):
    def GET(self, **data):
        args = {}
        return self.m.objects(**args).to_json()

    # post data comes in **data
    def POST(self, **data):
        # make sure post data passed in is ready to pass to mongo engine
        prep_data = getattr(self.m, 'prep_%s_data' % self.proprty)
        result, obj, data = prep_data(data)

        # Check if there were data validation errors
        if result:
            result = ['Data validation failed: %s' % ', '.join(result)]
            cherrypy.response.status = "400 Bad Request"
        else:
            try:
                obj.update(**data)
                cherrypy.response.status = "201 Resource Created"
                result.append('Added %s %s' % (self.proprty, data))
            except Exception, e:
                    # TODO: make sure when this is thrown the output
                    #       points back to here and gives the end user
                    #       enough information to fix the issue
                cherrypy.response.status = "500 Internal Server Error"
                result.append('Error: %s' % e)
        print result
        return json.dumps({'result': result})

    def PUT(self, **data):
        # update operations are done through POST
        # using PUT would duplicate most of POST
        return self.POST(**data)

    def DELETE(self, item, obj_name):
        obj = self._get_obj(obj_name)
        if obj:
            data = {'unset__%s__%s' % (self.proprty, item): True}
            obj.update(**data)
            result = ['deleted %s from %s' % (self.proprty, obj_name)]
        else:
            cherrypy.response.status = "404 Not Found"
            result = ['%s Not Found for %s %s'  % (self.proprty, self.name, obj_name)]
        return json.dumps({'result': result})

@cherrypy.expose
class QuadsServerApiV2(object):
    def __init__(self):
        self.cloud = DocumentMethodHandler(m.Cloud, 'cloud')
        self.owner = DocumentMethodHandler(m.Cloud, 'owner')
        self.ccuser = DocumentMethodHandler(m.Cloud, 'ccuser')
        self.ticket = DocumentMethodHandler(m.Cloud, 'ticket')
        self.qinq = DocumentMethodHandler(m.Cloud, 'qinq')
        self.wipe = DocumentMethodHandler(m.Cloud, 'wipe')
        self.host = DocumentMethodHandler(m.Host, 'host')
        self.schedule = PropertyMethodHandler(m.Host, 'host', 'schedule')
        self.interfaces = PropertyMethodHandler(m.Host, 'host', 'interfaces')