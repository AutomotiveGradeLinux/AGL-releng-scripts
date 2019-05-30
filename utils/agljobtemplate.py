#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import jinja2
import ConfigParser
import urlparse
import ast


def get_extension(path):
    return path.split('.')[-1]


def parse_cfg_file(template_path, cfg_file, build_type):
    url_file_path = template_path + '/config/' + cfg_file
    try:
        with open(url_file_path):
            cfg = ConfigParser.ConfigParser()
            cfg.read(url_file_path)
            return cfg.items(build_type), cfg.get('infra', 'style')
    except IOError as err:
        raise err


def parse_callback_file(template_path, lava_callback, kci_callback):
    callback_file_path = template_path + '/callback/' + lava_callback + '.cfg'
    try:
        with open(callback_file_path):
            cfg = ConfigParser.ConfigParser()
            cfg.read(callback_file_path)
            if kci_callback is None:
                kci_callback = cfg.get('default', 'section')
                kci_callback = kci_callback.split(',')
            cb_data = []
            for callback_target in kci_callback:
                cb_data.append(dict(cfg.items(callback_target)))
            return cb_data
    except (ConfigParser.NoSectionError) as err:
        str_err = "'--callback-to {}': must correspond to a section [{}] in the file '{}.cfg'".format(
            kci_callback, kci_callback, lava_callback)
        raise ConfigParser.NoSectionError(str_err)
    except (IOError) as err:
        str_err = "\n'--callback-from {}': must correspond to a file located in: ".format(lava_callback)
        str_err += "[releng-scripts]/templates/callback/{}.cfg".format(lava_callback)
        raise IOError(err, str_err)

class Agljobtemplate(object):

    DEFAULT_PATH = "templates"
    CALLBACK_DIR = "callback"
    MACHINES_DIR = "machines"
    MACHINES_BRANCH_DIR = "machines-branch"
    TESTS_DIR = "tests"
    RFS_TYPE = ['nbd', 'ramdisk']

    def __init__(self, path=DEFAULT_PATH):
        try:
            from jinja2 import select_autoescape
        except ImportError:
            raise ImportError("Please make sure your version of jinja2 is >= 2.9")
        self._template_path = os.path.normpath(path)
        if not (os.path.isdir(self._template_path) and os.access(self._template_path, os.F_OK)):
            raise OSError("Cannot access {}".format(self._template_path))

        if self.machines is None:
            raise RuntimeError("No machine directory found at {}".format(self._template_path))

    def __list_jinjas(self, directory):
        d = os.path.join(self._template_path, directory)
        return [os.path.splitext(os.path.basename(f))[0] for f in os.listdir(d) if f.endswith('.jinja2')]

    @property
    def machines(self):
        """ List the availables machines
        """
        return self.__list_jinjas(self.MACHINES_DIR)

    @property
    def tests(self):
        """ List the availables tests
        """
        return self.__list_jinjas(self.TESTS_DIR)

    @property
    def rfs_types(self):
        return self.RFS_TYPE

    def render_job(self, machine, url=None, changeid=None, patchset=None, version=None,
                   job_name="AGL-short-smoke", priority="medium", tests=[], rfs_type=None,
                   lava_callback=None, kci_callback=None, build_id=None,
                   rfs_image=None, kernel_image=None, dtb_image=None, modules_image=None,
                   build_type=None, vcs_commit=None, vcs_branch=None,
                   build_version=None, device_tags="",
                   applications_url=None, app_changeid=None, app_patchset=None, app_branch=None):

        if machine not in self.machines:
            raise RuntimeError("{} is not a available machine".format(machine))

        # Populate jinja substitution dict
        job = {}
        job['name'] = job_name
        job['yocto_machine'] = machine
        job['priority'] = priority
        job['build_type'] = build_type
        job['image_type'] = "AGL-%s" % build_type

        defaults, infra = parse_cfg_file(self._template_path, 'default.cfg', build_type)

        # If the user doesn't specify an URL, use the default one from the build-type

        if url is None:
            if infra == 'AGL':
                url_base = ''
                for section in defaults:
                    if section[0] == "urlbase":
                        url_base = section[1]

                url_fragment = ''
                if (build_type == 'ci'):
                    url_fragment += changeid + '/' + patchset + '/'
                else:
                    url_fragment += vcs_branch + '/' + version + '/'

                machine_frag_url = machine
                if (machine == 'm3ulcb'):
                    machine_frag_url = machine + '-nogfx'
                if machine == "upsquare":
                    machine_frag_url = "intel-corei7-64"
                url_fragment += machine_frag_url

                if (build_type != 'ci'):
                    url_fragment += '/deploy/images/' + machine_frag_url

                url = urlparse.urljoin(url_base, url_fragment)

        if applications_url is None:
                app_url_base = ''
                # WGT will be always uploaded in ci
                appdefaults, appinfra = parse_cfg_file(self._template_path, 'default.cfg', 'ci')
                for section in appdefaults:
                    if section[0] == "urlbase":
                        app_url_base = section[1]

                job['app_changeid'] = app_changeid
                job['app_patchset'] = app_patchset
                job['app_branch'] = app_branch
                job['app_url_base'] = app_url_base
                job['APPURL'] = 'automatic'
        else:
                job['APPURL'] = applications_url

        job['DEVICE_TAGS'] = device_tags

        test_templates = []
        # If the user doesn't specify tests, use the default ones from the build-type
        if not tests:
            if infra == 'AGL':
                for section in defaults:
                    if section[0] == "test_plan":
                        tests = ast.literal_eval(section[1])

        if 'all' in tests:
            tests = self.tests
        for t in tests:
            if t in self.tests:
                test_templates.append(os.path.join(self.TESTS_DIR, t + '.jinja2'))
            else:
                raise RuntimeError("{} is not an available test".format(t))

        job['urlbase'] = url

        job['test_templates'] = test_templates

        if vcs_commit is not None:
            job['vcs_commit'] = vcs_commit

        if vcs_branch is not None:
            job['vcs_branch'] = vcs_branch

        if build_version is not None:
            job['kernel_version'] = build_version

        if build_id is not None:
            job['kernel_defconfig'] = build_id

        if rfs_type is not None:
            job['rootfs_type'] = rfs_type

        if rfs_image is not None:
            job['rfs_image'] = rfs_image

        if kernel_image is not None:
            job['kernel_image'] = kernel_image

        if dtb_image is not None:
            job['dtb'] = dtb_image

        if changeid is not None:
            job['change_id'] = changeid

        if patchset is not None:
            job['patch_set'] = patchset

        if modules_image is not None:
            job['modules'] = modules_image

        if lava_callback:
            job['do_callback'] = True
            job['callback_to_list'] = parse_callback_file(self._template_path, lava_callback, kci_callback)

        env = jinja2.Environment(loader=jinja2.FileSystemLoader(self._template_path))
        env.filters['get_extension'] = get_extension

        machine_branch = machine + '-' + vcs_branch + '.jinja2'

        if machine_branch in os.listdir(os.path.join(self._template_path, self.MACHINES_DIR, self.MACHINES_BRANCH_DIR)):
            template = env.get_template(os.path.join(self.MACHINES_DIR, self.MACHINES_BRANCH_DIR, machine_branch))
        else:
            template = env.get_template(os.path.join(self.MACHINES_DIR, machine + ".jinja2"))

        return template.render(job)
