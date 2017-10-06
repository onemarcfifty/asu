#!/usr/bin/env python3

from flask import Flask
from flask import render_template, request, send_from_directory, redirect, jsonify
import json
import socket
import os
import logging
from http import HTTPStatus

from server.update_request import UpdateRequest
from server.image_request import ImageRequest
from server import app

import utils
from utils.config import Config
from utils.database import Database
from utils.common import get_dir, create_folder, init_usign

database = Database()
config = Config()

@app.route("/update-request", methods=['POST'])
def update_request():
    if request.method == 'POST':
        request_json = request.get_json()
        ur = UpdateRequest(request_json)
        return ur.run()
    return 400

# direct link to download a specific image based on hash
@app.route("/download/<path:image_path>/<path:image_name>")
def download_image(image_path, image_name):
    database.increase_downloads(os.path.join(image_path, image_name))

    # use different approach?
    if not config.get("dev"):
        return redirect(os.path.join(config.get("update_server"), "static", image_path, image_name), HTTPStatus.FOUND)
    return send_from_directory(directory=os.path.join(get_dir("downloaddir"), image_path), filename=image_name)

# request methos for individual image
# uses post methos to receive build information

# the post request should contain the following entries
# distribution, version, revision, target, packages
@app.route("/image-request", methods=['GET', 'POST'])
def requst_image():
    if request.method == 'POST':
        request_json = request.get_json()
        ir = ImageRequest(request_json, 1)
        return ir.get_sysupgrade()

# may show some stats
@app.route("/")
def root_path():
    return render_template("index.html",
            popular_subtargets=database.get_popular_subtargets(),
            worker_active=database.get_worker_active(),
            images_count=database.get_images_count(),
            images_total=database.get_images_total(),
            packages_count=database.get_packages_count())

@app.route("/api/<function>")
def api(function):
    data = '[]'
    status = 200
    if function == "distros":
        data = database.get_supported_distros()
    elif function == "releases":
        distro = request.args.get("distro", "")
        data = database.get_supported_releases(distro)
    elif function == "models":
        print("yea")
        distro = request.args.get("distro", "")
        release = request.args.get("release", "")
        model_search = request.args.get("model_search", "")
        print(model_search)
        data = database.get_supported_models(model_search, distro, release)
    elif function == "network_profiles":
        data = utils.common.get_network_profiles()
    else:
        status=404
    response = app.response_class(response=data, status=status, mimetype='application/json')
    return response

@app.route("/supported")
def supported():
    show_json = request.args.get('json', False)
    if show_json:
        distro = request.args.get('distro', '%')
        release = request.args.get('release', '%')
        target = request.args.get('target', '%')
        supported = database.get_subtargets_json(distro, release, target)
        return supported
    else:
        supported = database.get_subtargets_supported()
        return render_template("supported.html", supported=supported)

@app.route("/images")
def images():
    images = database.get_images_list()
    return render_template("images.html", images=images)

@app.route("/manifest-info/<manifest_hash>")
def image_info(manifest_hash):
    manifest = database.get_manifest_info(manifest_hash)
    return render_template("manifest-info.html", manifest=manifest)