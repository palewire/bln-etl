"""Light-weight BLN API wrappers to simplify CRUD
"""
import requests

from .queries import (
    DELETE_FILE_QUERY,
    OPEN_PROJECTS_QUERY,
    PROJECT_QUERY,
    PROJECT_FILES_QUERY,
    USER_PROJECTS_QUERY,
)


ENDPOINT = 'https://api.biglocalnews.org/graphql'


class ApiError(Exception): pass
class ConfigurationError(Exception): pass


class Base:

    @classmethod
    def post(cls, api_token, data):
        headers = {'Authorization': f'JWT {api_token}'}
        resp = requests.post(
            ENDPOINT,
            json=data,
            headers=headers
        )
        return resp.json()

    @classmethod
    def _prepare_project_kwargs(cls, node):
        kwargs = node
        kwargs['uuid'] = kwargs.pop('id')
        kwargs['created_at'] = kwargs.pop('createdAt')
        kwargs['updated_at'] = kwargs.pop('updatedAt')
        kwargs['contact_method'] = kwargs.pop('contactMethod')
        kwargs['is_open'] = kwargs.pop('isOpen')
        #name = kwargs.pop('name')
        #kwargs['api_token'] = self.api_token
        return kwargs


class Client(Base):

    def __init__(self, api_token):
        self.api_token = api_token

    @property
    def user_projects(self):
        data = {
            'query': USER_PROJECTS_QUERY,
            'variables': {}
        }
        response = self.post(self.api_token, data)
        try:
            raise ApiError(response['errors'])
        except KeyError:
            projects = []
            for edge in response['data']['user']['effectiveProjectRoles']['edges']:
                node = edge['node']
                kwargs = self._prepare_project_kwargs(node['project'])
                kwargs = node['project']
                kwargs['user_role'] = node['role']
                name = kwargs.pop('name')
                project = Project(name, **kwargs)
                projects.append(project)
            return projects

    @property
    def open_projects(self):
        data = {
            'query': OPEN_PROJECTS_QUERY,
            'variables': {}
        }
        response = self.post(self.api_token, data)
        projects = []
        for node in response['data']['openProjects']['edges']:
            kwargs = self._prepare_project_kwargs(node['node'])
            name = kwargs.pop('name')
            project = Project(name, **kwargs)
            projects.append(project)
        return projects


class File(Base):

    def __init__(self, api_token, project_id, name):
        self.api_token = api_token
        self.project_id = project_id
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()

    def delete(self):
        variables = {
            "input":{
                "fileName": self.name,
                "projectId":self.project_id,
            }
        }
        data = {
            "operationName":"DeleteFile",
            'query': DELETE_FILE_QUERY,
            'variables': variables
        }
        return self.post(self.api_token, data)


class Files(Base):

    def __get__(self, obj, owner):
        try:
            return obj._files
        except AttributeError:
            resp = self._get_files(obj)
            obj._files = [
                File(obj.api_token, obj.project.id, node['name'])
                for node in resp['data']['node']['files']
            ]
            return obj._files

    def _get_files(self, obj):
        data = {
            'query': PROJECT_FILES_QUERY,
            'variables': {
                'id': obj.project.id
            }
        }
        return self.post(obj.api_token, data)


class Project(Base):

    files = Files()

    def __init__(self, name,
        uuid=None,
        description='',
        is_open=None,
        contact=None,
        contact_method=None,
        user_role=None,
        created_at=None,
        updated_at=None,
        api_token=None
        ):
        self.name = name
        self.id = uuid
        self.description = description
        self.is_open = is_open
        self.contact = contact
        self.contact_method = contact_method
        self.user_role = user_role
        self.created_at = created_at
        self.updated_at = updated_at
        self.api_token = api_token

    def __str__(self):
        return f"<BLN Project: {self.slug}>"

    def __repr__(self):
        return self.__str__()

    @property
    def slug(self):
        slug = self.name[:20].lower().replace(' ','-')
        if self.id:
            slug += f"-{self.id[:15]}"
        return slug

    @classmethod
    def get(cls, uuid, api_token=None):
        if not api_token:
            try:
                api_token = os.environ['BLN_API_KEY']
            except KeyError:
                msg = (
                    "You must pass an api_token argument "
                    "or set the BLN_API_KEY "
                    "environment variable."
                )
                raise ConfigurationError(msg)
        data = {
            'query': PROJECT_QUERY,
            'variables': { "id": uuid }
        }
        response = cls.post(api_token, data)
        project_node = response['data']['node']
        if project_node:
            kwargs = cls._prepare_project_kwargs(project_node)
            name = kwargs.pop('name')
            return cls(name, **kwargs)
