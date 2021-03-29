#!/usr/bin/env python3

import argparse
import requests
from urllib.parse import urljoin
import os
import json
import urllib

parser = argparse.ArgumentParser(description="AGL create bmeta", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--arch', action='store', help="arch of the build", required=True)
parser.add_argument('--branch', action='store', help="branch of the build", required=True)
parser.add_argument('--commit', action='store', help="commit of the build", required=True)
parser.add_argument('--build_version', action='store', help="build_version of the build", required=True)
parser.add_argument('--kernel_version', action='store', help="kernel_version of the build", default=None)
parser.add_argument('--machine', action='store', help="machine of the build", required=True)
parser.add_argument('--api', action='store', help="URL to kernelci backend API", required=True)
args = parser.parse_args()

KCI_PUSH_TOKEN = "AGL_KCIAPI_TOKEN"
KCI_UPLOAD_TOKEN = "AGL_KCIAPI_TOKEN"

if args.api == 'http://kernelci.dev.baylibre.com:8081/':
    KCI_PUSH_TOKEN = "BAY_KCIAPI_TOKEN"
    KCI_UPLOAD_TOKEN = "BAY_KCIAPI_TOKEN"

if not KCI_PUSH_TOKEN in os.environ:
    print("Missing env variable %s" % KCI_PUSH_TOKEN)
    ptoken=None
else:
    ptoken=os.environ[KCI_PUSH_TOKEN]
if not KCI_UPLOAD_TOKEN in os.environ:
    print("Missing env variable %s" % KCI_UPLOAD_TOKEN)
    utoken=None
else:
    utoken=os.environ[KCI_UPLOAD_TOKEN]

bmeta = {}
bmeta["arch"] = args.arch
bmeta["build_log"] = "build.log"
bmeta["build_environment"] = "AGL-yocto"
bmeta["defconfig"] = "defconfig"
bmeta["defconfig_full"] = "defconfig+CONFIG_AGL=y"

bmeta["git_branch"] = args.branch
bmeta["git_commit"] = args.commit
if args.kernel_version:
    bmeta["git_describe"] = args.kernel_version
else:
    bmeta["git_describe"] = args.branch
bmeta["job"] = "AGL-yocto"

fsr = "AGL-yocto/%s/%s/%s/" % (args.branch, args.build_version, args.machine)
bmeta["file_server_resource"] = fsr

print(bmeta)

DIR_META="agl-build-meta"
# create directory with artifacts to be uploaded (bmeta.json)
if not os.path.exists(DIR_META):
    os.mkdir(DIR_META)

# write bmeta in it
with open(os.path.join(DIR_META, 'bmeta.json'), 'w') as json_file:
    json.dump(bmeta, json_file, indent=4, sort_keys=True)

def upload():
    path = bmeta["file_server_resource"]

    data = {
        'path': path,
    }
    artifacts = {}
    for root, _, files in os.walk(DIR_META):
        for f in files:
            px = os.path.relpath(root, DIR_META)
            artifacts[os.path.join(px, f)] = open(os.path.join(root, f), "rb")

    files = {
        'file{}'.format(i): (name, fobj)
        for i, (name, fobj) in enumerate(artifacts.items())
    }
    url = urljoin(args.api, 'upload')
    print("DATA====================")
    print(data)
    if utoken is None:
        print("No upload token, skipping upload")
        return 0
    headers = {
        'Authorization': utoken,
    }
    resp = requests.post(url, headers=headers, data=data, files=files)
    resp.raise_for_status()
    print(resp.reason)
    print(resp.text)


def publish_kernel():
    data = {k: bmeta[v] for k, v in {
        'file_server_resource': 'file_server_resource',
        'job': 'job',
        'git_branch': 'git_branch',
        'arch': 'arch',
        'kernel': 'git_describe',
        'build_environment': 'build_environment',
        'defconfig': 'defconfig',
        'defconfig_full': 'defconfig_full',
    }.items()}
    print("DATA====================")
    print(data)
    if ptoken is None:
        print("No publish token, skipping publish")
        return 0
    headers = {
        'Authorization': ptoken,
        'Content-Type': 'application/json',
    }
    url = urllib.parse.urljoin(args.api, '/build')
    data_json = json.dumps(data)
    resp = requests.post(url, headers=headers, data=data_json)
    resp.raise_for_status()
    print(resp.reason)
    print(resp.text)

print("============== UPLOAD")
upload()
print("============== PUBLISH")
publish_kernel()

