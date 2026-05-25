class ServiceCoreRouter:
    postgres_apps = {'transc', 'orders'}
    mongo_apps = {'catalog'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.postgres_apps:
            return 'postgresql_db'
        if model._meta.app_label in self.mongo_apps:
            return 'mongodb'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.postgres_apps:
            return 'postgresql_db'
        if model._meta.app_label in self.mongo_apps:
            return 'mongodb'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        labels = {obj1._meta.app_label, obj2._meta.app_label}
        if labels <= (self.postgres_apps | self.mongo_apps):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.postgres_apps:
            return db in {'default', 'postgresql_db'}
        if app_label in self.mongo_apps:
            return False
        return db in {'default', 'postgresql_db'}
