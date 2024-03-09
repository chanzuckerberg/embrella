from requests.exceptions import HTTPError
from utils.confluence import ConfluenceConnectionManager
from constant import SERVER, USERNAME, PAGE_ID, API_KEY
from bs4 import BeautifulSoup
from tabulate import tabulate

import logging
import requests
import pandas as pd
import json


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ConfluencePull(ConfluenceConnectionManager):
    def __init__(self, confluence_instance):
        super().__init__(confluence_instance.base_url, confluence_instance.auth, confluence_instance.headers)
        self.confluence = confluence_instance

    def get_page_by_id(self, page_id, **kwargs):
        if not isinstance(page_id, str):
            raise ValueError("Page ID must be a string.")
        url = '{}/wiki/api/v2/pages/{}'.format(self.confluence.base_url, page_id)
        params = {key.replace('_', '-'): value for key, value in kwargs.items() if value is not None}
        try:
            response = requests.get(url, headers=self.confluence.headers, auth=self.confluence.auth, params=params)
            response.raise_for_status()  # This will raise HTTPError for bad responses
            return response.json()
        except HTTPError as e:
            logger.exception("Failed to retrieve content by given ID or other HTTP error.")
            raise e

    def get_page_body_content(self, api_result):
        """
        get page body content from confluence page
        :param api_result: json
        :return page_body
        """
        try:
            if len(api_result) != 0:
                return api_result.get('body', {}).get('storage', {}).get('value', None)
        except Exception as e:
            logger.exception('Error occurred while getting the page from the confluence')
            raise e

    def get_all_macros(self, content):
        """
        get all macros from confluence page
        :param content
        return all macros from confluence page
        """
        try:
            # Create BeautifulSoup object
            soup = BeautifulSoup(content, 'html5lib')
            result = {}
            # Extract relevant structured-macro tags
            lst = soup.body.find_all('ac:structured-macro', {'ac:name': 'details'})

            # Iterate over each structured-macro tag
            for table in lst:
                # Extract macro-id and local-id attributes
                macro_id = table.get('ac:macro-id')
                local_id = table.get('ac:local-id')

                # Add macro-id and local-id to result dictionary
                if macro_id and local_id:
                    # Extract data from each table and create a DataFrame
                    table_data = []
                    for row in table.select('table tr'):
                        row_data = [cell.get_text() for cell in row.select('th, td')]
                        table_data.append(row_data)
                    df = pd.DataFrame(table_data)

                    # Add DataFrame, macro-id, and local-id to result dictionary
                    result[macro_id] = {"local-id": local_id, "table": df}

            return result
        except Exception as e:
            logger.exception("Error occurred while getting macros")
            raise e

    def get_tables_from_page(self, page_id):
        """
        Fetch html tables from confluence page
        :param page_id get page by id
        :return: list of tables
        """
        try:
            page_content = self.get_page_by_id(page_id, body_format="storage")["body"]["storage"]["value"]
            if page_content:
                tables_raw = [
                    [[cell.text for cell in row("th") + row("td")] for row in table("tr")]
                    for table in BeautifulSoup(page_content, features="lxml")("table")
                ]
                if len(tables_raw) > 0:
                    return json.dumps(
                        {
                            "page_id": page_id,
                            "number_of_tables_in_page": len(tables_raw),
                            "tables_content": tables_raw,
                        }
                    )
                else:
                    return {
                        "No tables found for page: ": page_id,
                    }
            else:
                return {"Page content is empty"}
        except Exception as e:
            logger.error("Error occurred while getting tables from the page")
            raise e

    def get_page_labels(self, page_id, prefix=None, sort=None, cursor=None, limit=None):

        """
        Returns the list of labels on a piece of Content.
        :param page_id: A string containing the id of the labels content container.
        :param prefix: OPTIONAL: The prefixes to filter the labels with {@see Label.Prefix}.
                                Default: None.
        :param start: OPTIONAL: The start point of the collection to return. Default: None (0).
        :param limit: OPTIONAL: The limit of the number of labels to return, this may be restricted by
                            fixed system limits. Default: 200.
        :return: The JSON data returned from the content/{id}/label endpoint, or the results of the
                 callback. Will raise requests.HTTPError on bad input, potentially.
        """
        url = "{}/wiki/api/v2/pages/{}/labels".format(self.confluence.base_url, page_id)
        params = {}
        if prefix:
            params["prefix"] = prefix
        if sort is not None:
            params["sort"] = str(sort)
        if cursor is not None:
            params["cursor"] = str(cursor)
        if limit is not None:
            params["limit"] = int(limit)

        try:
            response = requests.get(url, headers=self.confluence.headers, auth=self.confluence.auth, params=params)
            result = response.json()
            return [res['name'] for res in result.get('results')]
        except HTTPError as e:
            logger.exception("Failed to retrieve the label from the confluence wiki page")
            raise e

    @staticmethod
    def beautify_page_tables(data):
        if not isinstance(data, dict):
            raise ValueError("Input data should be dict type.")
        try:
            dataframes = []
            for id, value in data.items():
                # Assuming 'value.get('table')' returns a structure that can be directly converted to a DataFrame
                table_data = value.get('table')
                if table_data is not None:
                    df = pd.DataFrame(table_data)
                    # Use the one-liner to set the first row as headers and remove it
                    df.columns, df = df.iloc[0], df.reset_index(drop=True)
                    dataframes.append(df)
                else:
                    logger.error(f"No table found for ID: {id}")

            for i, df in enumerate(dataframes):
                print(f"--------------------------------------------------------Table - {i}--------------------------------------------------------")
                print(tabulate(df, headers='keys', tablefmt='grid'))
        except Exception as e:
            logger.error("Error occurred while beautifying the tables", exc_info=True)
            raise e


if __name__ == "__main__":
    manager = ConfluenceConnectionManager(base_url=SERVER, username=USERNAME, api_token=API_KEY)
    confluence = ConfluencePull(manager)
    result = confluence.get_page_by_id(PAGE_ID, body_format="storage")
    content = confluence.get_page_body_content(result)
    macros = confluence.get_all_macros(content)
    confluence.beautify_page_tables(macros)
    tables = confluence.get_tables_from_page(PAGE_ID)
    labels = confluence.get_page_labels(PAGE_ID)

