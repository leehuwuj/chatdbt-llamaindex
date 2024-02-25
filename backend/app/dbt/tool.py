import json
import yaml

from os import path
from typing import List, Optional
from llama_index.core.schema import Document
from llama_index.core.tools.tool_spec.base import BaseToolSpec
from dbt_artifacts_parser.parser import parse_manifest


class DbtToolSpec(BaseToolSpec):
    spec_functions = ["fetch_project_info", "fetch_project_schemas"]

    def __init__(self, project_dir: str):
        self.project_dir = project_dir

    def _fetch_project_meta(self) -> Document:
        dbt_meta_file = "dbt_project.yml"
        dbt_meta_path = path.join(self.project_dir, dbt_meta_file)
        if not path.exists(dbt_meta_path):
            raise FileNotFoundError(
                f"dbt project meta file {dbt_meta_file} not found in {self.project_dir}"
            )
        with open(dbt_meta_path) as f:
            dbt_meta = yaml.safe_load(f)

        return Document(
            text=f"Here is the dbt project meta information: {json.dumps(dbt_meta)}"
        )

    def _fetch_project_packages(self) -> Document:
        dbt_packages_file = "packages.yml"
        dbt_packages_path = path.join(self.project_dir, dbt_packages_file)
        if not path.exists(dbt_packages_path):
            raise FileNotFoundError(
                f"dbt project packages file {dbt_packages_file} not found in {self.project_dir}"
            )
        with open(dbt_packages_path) as f:
            dbt_packages = yaml.safe_load(f)

        return Document(
            text=f"Here is the dbt project packages information: {json.dumps(dbt_packages)}"
        )

    def _fetch_schemas(self) -> List[Document]:
        import glob

        docs = []

        schema_files = glob.glob(
            path.join(self.project_dir, "models/**/schema.yml"), recursive=True
        )

        for file in schema_files:
            with open(file) as f:
                docs.append(
                    Document(
                        text=f"- Schema {file.replace(self.project_dir, '')}: {json.dumps(yaml.safe_load(f))}\n"
                    )
                )
        return docs

    def fetch_project_info(self, fetch_type: Optional[str] = None) -> list[Document]:
        """
        Fetch information of the dbt project.
        fetch_type are: "packages" (external packages) or "meta" (basic project information) or None (both)
        """

        docs = []

        match fetch_type:
            case "meta":
                docs.append(self._fetch_project_meta())
            case "packages":
                docs.append(self._fetch_project_packages())
            case _:
                docs.append(self._fetch_project_meta())
                docs.append(self._fetch_project_packages())
        return docs

    def fetch_project_schemas(self) -> List[Document]:
        """
        Fetch schemas of the dbt project. Only call if you have a project directory and need to fetch the used databases, tables of project.
        """
        return self._fetch_schemas()


class DbtManifestToolSpec(BaseToolSpec):
    spec_functions = ["get_project_sources", "get_models_info", "get_model_sql"]

    def __init__(self, project_dir: str):
        self.project_dir = project_dir

    def _fetch_manifest(self):
        manifest_path = path.join(self.project_dir, "target/manifest.json")
        with open(manifest_path) as f:
            raw = json.loads(f.read())
            manifest = parse_manifest(raw)
            return manifest

    @staticmethod
    def get_sub_attributes(data, sub_attributes: list[str]):
        """
        Get sub attributes of a dictionary.
        """
        for sub_attribute in sub_attributes:
            dict_data = str(data.__getattribute__(sub_attribute))
        return dict_data

    def get_project_sources(self):
        """
        Get the source database information of dbt project.
        """
        manifest = self._fetch_manifest()
        sources_info = {
            source_id: source_value.json()
            for source_id, source_value in manifest.sources.items()
        }

        return Document(text=json.dumps(sources_info))

    def get_models_info(self, model_id: Optional[str] = None):
        """
        Get model information of the dbt project.
        pass model_id to get specific model information, dont pass to get all models information.
        """
        manifest = self._fetch_manifest()
        models_info = {
            model_id: self.get_sub_attributes(
                model_value,
                [
                    "database",
                    "schema",
                    "name",
                    "relation_name",
                    "path",
                    "unique_id",
                    "columns",
                    "depends_on",
                ],
            )
            for model_id, model_value in manifest.nodes.items()
            if model_id.startswith("model")
        }

        return Document(text=json.dumps(models_info))

    def get_model_sql(self, model_id: str):
        """
        Get the sql of the model. Use can reasoning the relation, columns of a model from sql result of this function
        Args: model_id: the id of the model, it should start with "model.schema.model_name"
        """
        manifest = self._fetch_manifest()
        model = manifest.nodes.get(model_id)
        return Document(text=model.compiled_code)


class DbtRunResultToolSpec(BaseToolSpec):
    spec_functions = ["get_run_result"]

    def __init__(self, project_dir: str):
        self.project_dir = project_dir

    def get_run_result(self):
        """
        Get the run result of the dbt project.
        """
        run_result_path = path.join(self.project_dir, "target/run_results.json")
        with open(run_result_path) as f:
            run_result = json.loads(f.read())
            return Document(text=json.dumps(run_result))
