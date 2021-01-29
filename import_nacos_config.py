#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import json, httplib, urllib, os, sys
import subprocess, re

NacosHostIP = os.environ.get('NacosHostIP', '192.168.24.22')
NacosHostPort = os.environ.get('NacosHostPort', 59494)
NacosUserName = os.environ.get('NacosUserName', 'nacos')
NacosUserPassword = os.environ.get('NacosUserPassword', 'nacos')
RetryInterval=int(os.environ.get('RetryInterval', 5))
RetryTimes=int(os.environ.get('RetryTimes', 10))
ConnectionTimeOut=int(os.environ.get('ConnectionTimeOut', 10))
DataDIR=os.environ.get('DataDIR', 'DATA/')



headers = {
    "Content-type": "application/x-www-form-urlencoded",
}

def checkConnection(func):
    def wrapper(*args, **kwargs):
        canConnect=False
        for itime in range(RetryTimes):
           try:
               TmpHttpObj=httplib.HTTPConnection(NacosHostIP, NacosHostPort ,timeout=ConnectionTimeOut)
               TmpHttpObj.request(url='nacos', method='GET')
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

@checkConnection
def get_namespaces():
    return sendHttpRequest(host=NacosHostIP, port=NacosHostPort, url='/nacos/v1/console/namespaces')

@checkConnection
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

@checkConnection
def create_namespace(namespace=None, namespaceID='6c0b3e50-8629-411a-a0ed-a270f327e8cd'):
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
def publish_config(tenant='wcm', dataid=None, group='DEFAULT_GROUP', content='', type='text'):
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

@checkConnection
def get_config(tenant='wcm', dataid=None, group='DEFAULT_GROUP'):
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
    if not os.path.isfile(os.path.join(DataDIR, 'namespace.txt')):
        print ('ERROR; namespace file not exits: '+str(os.path.join(DataDIR, 'namespace.txt')))
        exit(1)
    with open(os.path.join(DataDIR, 'namespace.txt'),mode='r') as f:
        for line in f:
            line = line.strip()
            TmpList = line.split()
            if len(TmpList) != 2:
                continue

            TmpNamespace = TmpList[0]
            TmpID = TmpList[1]
            create_namespace(namespace=TmpNamespace, namespaceID=TmpID)

    TmpDataDIR = os.path.normpath(DataDIR) + os.sep
    if not os.path.isdir(DataDIR):
        print ('ERROR; namespace file not exits: ' + str(DataDIR))
        exit(1)

    RawInfo = subprocess.Popen("find %s -mindepth 3 -maxdepth 3 -type f"%(TmpDataDIR,),shell=True,
                               stdout=subprocess.PIPE).communicate()[0]
    for filepath in re.findall(r'(.*?)\n', RawInfo, flags=re.MULTILINE|re.DOTALL|re.UNICODE):
        TmpFileExtension = filepath.split('.')[1]
        if TmpFileExtension not in ['yaml', 'yml', 'properties']:
            print ('Skipping: %s'%(filepath,))
            continue
        TmpFilename = filepath.lstrip(TmpDataDIR)
        if TmpFilename.count(os.sep) == 1:
            TmpGroupName = TmpFilename.split(os.sep)[0]
            print ('filename: '+str(filepath))
            print ('group name: '+str(TmpGroupName))
            with open(filepath) as f:
                print (u'导入 %s' % (filepath,))
                TmpResult = publish_config(dataid=filepath.split('/')[-1], content=f.read(), tenant=TmpGroupName)
                print (TmpResult)
                if TmpResult['ret_code'] != 0:
                    print (str(TmpResult))
                    sys.exit(1)
        elif TmpFilename.count(os.sep) == 2:
            TmpTenantName = TmpFilename.split(os.sep)[0]
            TmpFilename = TmpFilename.lstrip(TmpTenantName+'/')
            TmpGroupName = TmpFilename.split(os.sep)[0]

            print ('filename: '+str(filepath))
            print ('tenant name: %s'%(TmpTenantName,))
            print ('group name: '+str(TmpGroupName))
            with open(filepath) as f:
                print (u'load %s' % (filepath,))
                TmpResult = publish_config(dataid=filepath.split('/')[-1], content=f.read(), tenant=TmpTenantName, group=TmpGroupName)
                print (TmpResult)
                if TmpResult['ret_code'] != 0:
                    print (str(TmpResult))
                    sys.exit(1)


