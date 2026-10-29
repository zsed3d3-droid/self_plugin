"""Observable contract cases: database choice, actual persistence, legacy compatibility."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import yaml

SPEC = importlib.util.spec_from_file_location('container_contract', Path(__file__).resolve().parents[1] / 'scripts/check-containers.py')
contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)


class ContainerContractTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        (self.root / '.devtools').mkdir()
        (self.root / 'Dockerfile').write_text('FROM scratch\n')

    def write(self, manifest, compose):
        (self.root / '.devtools/services.json').write_text(json.dumps(manifest))
        (self.root / 'compose.yaml').write_text(yaml.safe_dump(compose))

    def pg(self, image='postgres:18.6', mounts=None, env=None, mode='service'):
        manifest = {'mode': mode, 'services': [{'name': 'db', 'image': image, 'database': 'postgres', 'persistent': True}]}
        compose = {'services': {'db': {'image': image, 'healthcheck': {'test': ['CMD', 'pg_isready']},
                    'volumes': mounts if mounts is not None else ['pgdata:/var/lib/postgresql']}}, 'volumes': {'pgdata': {}}}
        if env is not None:
            compose['services']['db']['environment'] = env
        self.write(manifest, compose)
        return manifest, compose

    def app(self, mode='service', database=None, env=None):
        service = {'name': 'app', 'dockerfile': 'Dockerfile'}
        if database:
            service['database'] = database
        manifest = {'services': [service]}
        if mode is not None:
            manifest['mode'] = mode
        entry = {'healthcheck': {'test': ['CMD', 'true']}}
        if env is not None:
            entry['environment'] = env
        compose = {'services': {'app': entry}}
        self.write(manifest, compose)
        return manifest, compose

    def test_service_sqlite_declaration_and_urls_are_rejected(self):
        for db, env in [('sqlite', None), (None, {'DATABASE_URL': 'sqlite:///data.db'}),
                        (None, ['DATABASE_URL=sqlite+aiosqlite:////data/app.db']),
                        (None, {'JDBC_URL': 'jdbc:sqlite:/data/app.db'}),
                        (None, {'SQLITE_PATH': '/data/app.db'})]:
            with self.subTest(db=db, env=env):
                self.app(database=db, env=env)
                with self.assertRaisesRegex(ValueError, 'SQLite'):
                    contract.check(self.root)

    def test_demo_and_legacy_remain_sqlite_compatible(self):
        for mode in ['demo', None]:
            with self.subTest(mode=mode):
                self.app(mode=mode, database='sqlite', env={'DATABASE_URL': 'sqlite:///app.db'})
                contract.check(self.root)

    def test_unknown_modes_and_database_values_fail(self):
        manifest, compose = self.app()
        for mode in ['production', 'legacy', None, '']:
            with self.subTest(mode=mode):
                manifest['mode'] = mode
                self.write(manifest, compose)
                with self.assertRaisesRegex(ValueError, 'mode'):
                    contract.check(self.root)
        manifest['mode'] = 'service'
        manifest['services'][0]['database'] = 'mysql'
        self.write(manifest, compose)
        with self.assertRaisesRegex(ValueError, 'database'):
            contract.check(self.root)

    def test_official_versioned_postgres_and_18_data_parent_pass(self):
        for image in ['postgres:18.6', 'docker.io/library/postgres:18.6-alpine',
                      'postgres:18.6-alpine3.23', 'postgres:19.1-trixie']:
            with self.subTest(image=image):
                self.pg(image=image)
                contract.check(self.root)

    def test_unpinned_prerelease_or_custom_postgres_fails(self):
        for image in ['postgres', 'postgres:latest', 'postgres:18', 'postgres:18rc1',
                      'postgres:18.6-beta', 'postgres:18.6-rc1', 'custom/postgres:18.6']:
            with self.subTest(image=image):
                manifest, compose = self.pg(image=image)
                # Dockerfile permits inspecting custom-image policy beyond the infrastructure shortcut.
                manifest['services'][0]['dockerfile'] = 'Dockerfile'
                self.write(manifest, compose)
                with self.assertRaisesRegex(ValueError, 'official postgres'):
                    contract.check(self.root)

    def test_postgres17_uses_legacy_data_path(self):
        self.pg(image='postgres:17.8', mounts=['pgdata:/var/lib/postgresql/data'])
        contract.check(self.root)
        self.pg(image='postgres:17.8', mounts=['pgdata:/var/lib/postgresql/18/docker'])
        with self.assertRaisesRegex(ValueError, 'PGDATA'):
            contract.check(self.root)

    def test_unrelated_readonly_anonymous_tmpfs_or_undeclared_mounts_fail(self):
        for mount in ['pgdata:/elsewhere', 'pgdata:/var/lib/postgresql/data',
                      'pgdata:/var/lib/postgresql:ro', '/var/lib/postgresql',
                      'not-declared:/var/lib/postgresql',
                      {'type': 'tmpfs', 'target': '/var/lib/postgresql'},
                      {'type': 'volume', 'source': 'pgdata', 'target': '/var/lib/postgresql', 'read_only': True}]:
            with self.subTest(mount=mount):
                self.pg(mounts=[mount])
                with self.assertRaisesRegex(ValueError, 'PGDATA'):
                    contract.check(self.root)

    def test_explicit_pgdata_and_bind_mount_pass(self):
        for env in [{'PGDATA': '/database/pgdata'}, ['PGDATA=/database/pgdata']]:
            with self.subTest(env=env):
                self.pg(mounts=[{'type': 'bind', 'source': './database', 'target': '/database'}], env=env)
                contract.check(self.root)
        self.pg(mounts=['/srv/postgres:/database'], env={'PGDATA': '/database/pgdata'})
        contract.check(self.root)

    def test_unresolved_or_traversing_pgdata_is_not_counted(self):
        for path in ['${PGDATA}', 'relative/data', '/database/../tmp/data']:
            with self.subTest(path=path):
                self.pg(env={'PGDATA': path})
                with self.assertRaises(ValueError):
                    contract.check(self.root)
        self.pg(mounts=['pgdata:/var/lib/postgresql/18/../'])
        with self.assertRaisesRegex(ValueError, 'traversal'):
            contract.check(self.root)

    def test_app_image_cannot_bypass_dockerfile_and_db_image_must_match(self):
        manifest, compose = self.app()
        manifest['services'][0].pop('dockerfile')
        manifest['services'][0]['image'] = 'nginx:1.27'
        compose['services']['app']['image'] = 'nginx:1.27'
        self.write(manifest, compose)
        with self.assertRaisesRegex(ValueError, 'Dockerfile'):
            contract.check(self.root)
        manifest, compose = self.pg()
        manifest['services'][0]['image'] = 'postgres:17.8'
        self.write(manifest, compose)
        with self.assertRaisesRegex(ValueError, 'Dockerfile'):
            contract.check(self.root)

    def test_disabled_healthcheck_fails_even_when_test_exists(self):
        for health in [{'test': ['NONE']}, {'test': ['CMD', 'true'], 'disable': True}, {}]:
            with self.subTest(health=health):
                manifest, compose = self.pg()
                compose['services']['db']['healthcheck'] = health
                self.write(manifest, compose)
                with self.assertRaisesRegex(ValueError, 'healthcheck'):
                    contract.check(self.root)

    def test_project_paths_cannot_escape_or_use_symlinks_outside(self):
        manifest, compose = self.app()
        with tempfile.TemporaryDirectory() as outside:
            file = Path(outside) / 'Dockerfile'
            file.write_text('FROM scratch\n')
            (self.root / 'linked-Dockerfile').symlink_to(file)
            for path in [str(file), 'linked-Dockerfile', '../Dockerfile']:
                with self.subTest(path=path):
                    manifest['services'][0]['dockerfile'] = path
                    self.write(manifest, compose)
                    with self.assertRaisesRegex(ValueError, 'relative|escapes'):
                        contract.check(self.root)
        manifest, compose = self.app()
        manifest['compose'] = '../compose.yaml'
        self.write(manifest, compose)
        with self.assertRaisesRegex(ValueError, 'escapes'):
            contract.check(self.root)

    def test_undeclared_duplicate_and_unapproved_host_services_fail(self):
        manifest, compose = self.app()
        compose['services']['extra'] = {'image': 'nginx'}
        self.write(manifest, compose)
        with self.assertRaisesRegex(ValueError, 'Undeclared'):
            contract.check(self.root)
        manifest, compose = self.app()
        manifest['services'].append(dict(manifest['services'][0]))
        self.write(manifest, compose)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            contract.check(self.root)
        manifest, compose = self.app()
        manifest['services'][0].update(host_exception=True, reason='easy', health_url='http://localhost')
        self.write(manifest, compose)
        with self.assertRaisesRegex(ValueError, 'mlx-transcriber'):
            contract.check(self.root)


if __name__ == '__main__':
    unittest.main()
