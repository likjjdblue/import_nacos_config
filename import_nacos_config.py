#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import json, httplib, urllib, os

NacosHostIP = os.environ.get('NacosHostIP', '192.168.24.22')
NacosHostPort = os.environ.get('NacosHostPort', 59494)
NacosUserName = os.environ.get('NacosUserName', 'nacos')
NacosUserPassword = os.environ.get('NacosUserPassword', 'nacos')
RetryInterval=int(os.environ.get('RetryInterval', 5))
RetryTimes=int(os.environ.get('RetryTimes', 10))
ConnectionTimeOut=int(os.environ.get('ConnectionTimeOut', 10))



headers = {
    "Content-type": "application/x-www-form-urlencoded",
}

def checkConnection(func):
    def wrapper(*args, **kwargs):
        canConnect=False
        for itime in range(RetryTimes):
           try:
               TmpHttpObj=httplib.HTTPConnection(NacosHostIP, NacosHostPort ,timeout=ConnectionTimeOut)
               TmpHttpObj.request(url='nacos')
               canConnect = True
               break
           except Exception as e:
               pass

        if not canConnect:
            return {
               "ret_code": 1,
               'result': u'无法连接:  %s:%s'%(str(NacosHostIP), str(NacosHostPort))
            }
        return func(*args, **kwargs)
    return wrapper



def sendHttpRequest(host='127.0.0.1', port=9200, url='/', method='GET', body={}, header={}, timeout=5):
    try:
        tmpBody = urllib.urlencode(body) if body else ''
        HttpObj = httplib.HTTPConnection(host, port, timeout=timeout)
        #        HttpObj.request(url=url,method=method,body=tmpBody,headers=header)

        if method.upper() == 'GET':
            TmpURL = url + '/?' + tmpBody if tmpBody else url
            HttpObj.request(url=TmpURL, method=method)
        else:
            HttpObj.request(url=url, method=method, body=tmpBody, headers=header)

        response = HttpObj.getresponse()
        data = response.read()
        return {
            'ret_code': 0,
            "result": data
        }

    except Exception as e:
        return {
            'ret_code': 1,
            "result": str(e)
        }


def get_namespaces():
    return sendHttpRequest(host=NacosHostIP, port=NacosHostPort, url='/nacos/v1/console/namespaces')


def get_namespace(namespace=None):
    if not namespace:
        return {
            "ret_code": 1,
            'result': u'参数不合法',
        }

    TmpResult = get_namespaces()
    if TmpResult['ret_code'] != 0:
        return TmpResult

    TmpList = json.loads(TmpResult['result'])['data']

    for item in TmpList:
        if item['namespaceShowName'] == namespace:
            return {
                'ret_code': 0,
                'result': item
            }
    return {'ret_code': 0, 'result': None}


def create_namespace(namespace=None, namespaceID=''):
    if not namespace or not isinstance(namespace, str):
        return {
            'ret_code': 1,
            "result": u"namespace 参数不合法：%s" % (str(namespace, ))
        }

    TmpResult = get_namespaces()
    if TmpResult['ret_code'] != 0:
        return TmpResult

    TmpList = json.loads(TmpResult['result'])['data']
    TmpCurrentNamespace = [x['namespaceShowName'] for x in TmpList]

    if namespace in TmpCurrentNamespace:
        return {
            "ret_code": 0,
            'result': "namespace %s already exists" % (namespace,)
        }

    TmpDict = {
        'username': NacosUserName,
        'password': NacosUserPassword,
        'namespaceName': namespace,
        'customNamespaceId': namespaceID,
        'namespaceDesc': namespaceID,
    }

    return sendHttpRequest(host=NacosHostIP, port=NacosHostPort, method='POST', url='/nacos/v1/console/namespaces',
                           body=TmpDict, header=headers)

@checkConnection
def publish_config(tenant='bigdata', dataid=None, group='DEFAULT_GROUP', content='', type='text'):
    if not dataid:
        return {
            'ret_code': 1,
            'result': u"dataid 参数不合法",
        }

    TmpNamespaceInfo = get_namespace(tenant)
    if TmpNamespaceInfo['result'] is None:
        RawCreateNamespace = create_namespace(tenant)
        if RawCreateNamespace['ret_code'] != 0 or RawCreateNamespace['result'] is None:
            return {'ret_code': 1, 'result': u"名空间 %s 不存在，且创建失败" % (tenant,)}
    TmpNamespaceInfo = get_namespace(tenant)

    TmpDict = {
        'username': NacosUserName,
        'password': NacosUserPassword,
        'tenant': TmpNamespaceInfo['result']['namespace'],
        'dataId': dataid,
        'content': content,
        'type': 'text',
        'group': group,
    }

    TmpResult = sendHttpRequest(host=NacosHostIP, port=NacosHostPort, url='/nacos/v1/cs/configs', method='POST',
                                body=TmpDict, header=headers)
    return TmpResult


def get_config(tenant='bigdata', dataid=None, group='DEFAULT_GROUP'):
    if not dataid:
        return {
            'ret_code': 1,
            'result': u"dataid 参数不合法",
        }

    TmpNamespaceInfo = get_namespace(tenant)
    if TmpNamespaceInfo['result'] is None:
        return {"ret_code": 0, "result": None}

    TmpDict = {
        'username': NacosUserName,
        'password': NacosUserPassword,
        'dataId': dataid,
        'tenant': TmpNamespaceInfo['result']['namespace'],
        'group': group,
    }

    TmpResult = sendHttpRequest(host=NacosHostIP, port=NacosHostPort, url='/nacos/v1/cs/configs', method='GET',
                                body=TmpDict)
    return TmpResult


if __name__ == "__main__":
    for a, b, c in os.walk('DEFAULT_GROUP'):
        if a == 'DEFAULT_GROUP':
            for filename in c:
                with open(os.path.join(a, filename)) as f:
                    print (u'导入 %s' % (filename,))
                    publish_config(dataid=filename, content=f.read())

