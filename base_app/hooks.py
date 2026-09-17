import os

from odoo.release import version_info


def post_init_hook(env):
    AMV = env["app.module.version"]
    AMV.post_init_hook()
    AMV.create_missing_versions()

    def get_path(relative_path):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(current_dir, relative_path)
        path = os.path.normpath(path)
        return path

    version = version_info[0]

    AMV.import_minutes_worked(get_path(f"data/{version}.csv"))
    AMV.import_migration_minutes(get_path(f"oow/{version}-{version + 1}.csv"))
