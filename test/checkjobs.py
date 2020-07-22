#!/usr/bin/python3

import re
import yaml
import os
import xmlrpc.client

lserver = xmlrpc.client.ServerProxy(os.getenv("LAVAURI"), allow_none=True)

offset = 0
while offset < 100:
    jlist = lserver.scheduler.jobs.list('FINISHED', None, offset, 100, None, False)
    for job in jlist:
        if job["submitter"] == 'lava-health':
            continue
        jobid = job["id"]
        print(jobid)
        job_out_raw = lserver.scheduler.job_output(jobid)
        job_out = yaml.safe_load(job_out_raw.data)
        for job_out_line in job_out:
            if job_out_line["lvl"] == 'debug' and isinstance(job_out_line["msg"], str) and re.search('APPURL=', job_out_line["msg"]):
                print(job_out_line)
            if job_out_line["lvl"] == 'target' and re.search('WGTNAME=', job_out_line["msg"]):
                print(job_out_line)
            if job_out_line["lvl"] == 'target' and re.search('ERROR', job_out_line["msg"]):
                print(job_out_line)
    offset += 100
