#!/usr/bin/env python3

import time
import json
import os
from argparse import ArgumentParser

import requests

# HTTP Header Values
headers = {
    'Content-Type': 'application/json;charset=UTF-8',
    'X-PowerBI-ResourceKey': 'd2b08558-c2e1-4763-a0a5-376485fd1dee',
    'Origin': 'https://app.powerbi.com',
}
params = {
    'synchronous': 'true',
}

# Route specifier
with open('body.json', 'r') as f:
    json_data = json.load(f)

json_route_dict = json_data['queries'][0]['Query']['Commands'][0] \
                           ['SemanticQueryDataShapeCommand']['Query']['Where'] \
                           [0]['Condition']['In']['Values'][0][0]['Literal'] \

# List of routes
routes = []
with open('routes.txt', 'r') as f:
    for line in f:
        routes.append(line.strip())

def parse():
    parser = ArgumentParser()
    parser.add_argument("export", help="path to the export directory")
    parsed = parser.parse_args()

    return parsed.export

def make_path(export_path):
    if not os.path.exists(export_path):
        os.mkdir(export_path, mode=0o700)
    if os.path.isfile(export_path):
        raise FileExistsError(f'Directory "{export_path}" is a file.')

    return export_path

def main(export_path):
    export_path = make_path(export_path)

    for route in routes:
        json_route_dict['Value'] = "'" + route + "'"

        timestr = time.strftime("%Y_%m_%d-%H_%M")
        print(export_path, route, timestr)
        filepath = os.path.join(export_path, route + '_' + timestr + '.json')
        with open(filepath, 'x') as file:
            response = requests.post(
                'https://wabi-us-east-a-primary-api.analysis.windows.net/public/reports/querydata',
                params=params,
                headers=headers,
                json=json_data,
            )
            file.write(response.text)
        print(response.text)
        print(filepath)
        time.sleep(0.5)


if __name__ == '__main__':
    export_path = parse()
    main(export_path)
