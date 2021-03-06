#!/usr/bin/env python

"""
Admin interface to osmo.
"""

import db
import errno
import flask
import os
import subprocess
import time
import werkzeug.utils
from config import config


app = flask.Flask(__name__)
app.secret_key = os.urandom(32)
d = db.Database()

def _static_dir(path):
    """
    Return a path within the static files directory.

    :param path: the path to append
    :returns: the path, prepended with the path to the static files directory
    :rtype: str
    """

    return os.path.join(os.path.dirname(__file__), "templates/static/" + path)


def _pdf_to_jpg(name, remove=True):
    """
    Convert a PDF to a JPG.

    :param name: the file to convert
    :param remove: whether to remove the PDF
    :returns: the name of the newly created file
    """

    new_name = "%s.jpg" % name.rsplit(".", 1)[0]

    subprocess.check_call((
        "convert", "-colorspace", "RGB", "-density", "300", "%s[0]" % name,
        "-flatten", new_name
    ))

    if remove:
        os.remove(name)

    return new_name


def _dtpicker_strptime(dtpicker_time):
    """
    Convert a dtpicker generated time into an epoch.

    :param dtpicker_time: the time format as generated by dtpicker
    :type dtpicker_time: str
    :returns: the associated epoch
    :rtype: int
    """

    time_struct = time.strptime(dtpicker_time, "%Y-%m-%d %H:%M")
    return time.mktime(time_struct)

def _allowed_file(filename):
    return any(
        filename.lower().endswith("." + x.lower())
        for x in config["admin"]["valid_extensions"]
    )


@app.route("/", methods=["GET"])
def list_all():
    """
    List all slides.

    :returns: the admin interface index
    :rtype: :class:`flask.Response`
    """

    return flask.render_template(
        "admin/index.html",
        slides=d.slides_in_state("all", sort="start"),
        active_slides=d.slides_in_state("active"),
        error=flask.request.args.get("error", 0),
    )


@app.route("/rem/<path:slide_name>", methods=["GET"])
def rem(slide_name):
    """
    Remove a slide.

    :param slide_name: the slide name to remove
    :returns: a redirect to the admin interface index
    :rtype: :class:`flask.Response`
    """

    name = werkzeug.utils.secure_filename(slide_name)
    try:
        os.remove(os.path.join(config["paths"]["media_dir"], name))
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise e
        else:
            flask.flash("""Slide "%s" does not exist!""" % name)
            return flask.redirect(flask.url_for("list_all") + "?error=1")
    d.remove(name)
    flask.flash("""Okay, deleted slide "%s".""" % name)
    return flask.redirect(flask.url_for("list_all"))


@app.route("/add", methods=["GET", "POST"])
def add():
    """
    Add a slide.

    :returns: if a POST, a redirect to the admin interface index, if a GET, the
        interface to add a slide
    :rtype: :class:`flask.Response`
    """

    if flask.request.method == "POST":
        u_file = flask.request.files["file"]

        name = werkzeug.utils.secure_filename(u_file.filename)

        start = flask.request.form["start"]
        end = flask.request.form["end"]
        duration = flask.request.form["duration"]
        rank = flask.request.form["rank"]

        errors = False

        if not u_file or not start or not end or not duration or not rank:
            errors = True
            flask.flash("Please enter all the fields.")

        if not _allowed_file(name):
            errors = True
            allowed_ext = ', '.join(config["admin"]["valid_extensions"])
            flask.flash(
                "Only these filename extensions are allowed: " + allowed_ext
            )

        if errors:
            return flask.render_template("admin/add.html")

        start = _dtpicker_strptime(start)
        end = _dtpicker_strptime(end)
        duration = int(duration)
        rank = int(rank)

        save_path = os.path.join(config["paths"]["media_dir"], name)
        u_file.save(save_path)

        if save_path.endswith(".pdf"):
            name = os.path.basename(_pdf_to_jpg(save_path))

        d.add(name, start, end, duration, rank)
        flask.flash("""Okay, created slide "%s".""" % name, 'success')
        return flask.redirect(flask.url_for("list_all"))
    return flask.render_template("admin/add.html")


@app.route('/static/js/<path:filename>')
def static_js(filename):
    """
    Return a file relative to the static Javascript directory.

    :returns: a file relative to the static directory
    :rtype: :class:`flask.Response`
    """

    return flask.send_from_directory(_static_dir("js"), filename)


@app.route('/static/css/<path:filename>')
def static_css(filename):
    """
    Return a path to a file relative to the static CSS directory.

    :returns: a file relative to the static directory
    :rtype: :class:`flask.Response`
    """

    return flask.send_from_directory(_static_dir("css"), filename)


@app.route('/static/img/<path:filename>')
def static_img(filename):
    """
    Return a path to a file relative to the static image directory.

    :returns: a file relative to the static directory
    :rtype: :class:`flask.Response`
    """

    return flask.send_from_directory(_static_dir("img"), filename)


if __name__ == "__main__":
    app.run(port=config["admin"]["port"],debug=config["admin"]["debug"])
