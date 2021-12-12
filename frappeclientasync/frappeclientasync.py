# -*- coding: utf-8 -*-
import aiohttp
import asyncio
import json
from base64 import b64encode
from urllib.parse import quote

try:
    unicode
except NameError:
    unicode = str

class FrappeClientAsync(object):
	def __init__(self, url=None, api_key=None, api_secret=None, verify=True):
		self.headers = dict(Accept='application/json')
		self.session = aiohttp.ClientSession()

		self.can_download = []
		self.verify_ssl = verify
		self.url = url

		if api_key and api_secret:
			self.authenticate(api_key, api_secret)
			self.session.headers.update(self.headers)

	def authenticate(self, api_key, api_secret):
		token = b64encode('{}:{}'.format(api_key, api_secret).encode()).decode()
		auth_header = {'Authorization': 'Basic {}'.format(token)}
		self.session.headers.update(auth_header)

	async def get_doc(self, doctype, name="", filters=None, fields=None):
		'''Returns a single remote document

		:param doctype: DocType of the document to be returned
		:param name: (optional) `name` of the document to be returned
		:param filters: (optional) Filter by this dict if name is not set
		:param fields: (optional) Fields to be returned, will return everythign if not set'''
		params = {}
		if filters:
			params["filters"] = json.dumps(filters)
		if fields:
			params["fields"] = json.dumps(fields)

		return await self.session.get(self.url + '/api/resource/' + doctype + '/' + name, params=params,verify_ssl=self.verify_ssl)

	async def get_count(self, doctype, filters=None):
		'''Returns the number of records that match the current filters'''
		params = {}
		if filters:
			params["filters"] = json.dumps(filters)
		params["doctype"] = doctype
		return self.post_process(await self.session.get(self.url + '/api/method/frappe.client.get_count', params=params))

	async def get_list(self, doctype, fields='"*"', filters=None, limit_start=0, limit_page_length=0, order_by=None):
		'''Returns list of records of a particular type'''
		if not isinstance(fields, unicode):
			fields = json.dumps(fields)
		params = {
			"fields": fields,
		}
		if filters:
			params["filters"] = json.dumps(filters)
		if limit_page_length:
			params["limit_start"] = limit_start
			params["limit_page_length"] = limit_page_length
		if order_by:
			params['order_by'] = order_by

		return self.post_process(await self.session.get(self.url + "/api/resource/" + doctype, params=params,
			verify_ssl=self.verify_ssl, headers=self.headers))

	async def simult_bulk_get_list(self, doctype, fields='"*"', filters=None, limit_page_length=0, order_by=None):
		'''Get simultanaeous bulks from doctype'''
		resp = await self.get_count(doctype, filters)
		num_docs = await resp
		tasks = []
		for i in range(0, num_docs, limit_page_length):
			tasks.append(self.get_list(doctype, fields, filters, i, limit_page_length, order_by=order_by))

		return await asyncio.gather(*tasks)

	async def insert(self, doc):
		'''Insert a document to the remote server

		:param doc: A dict or Document object to be inserted remotely'''
		return await self.session.post(self.url + "/api/resource/" + quote(doc.get("doctype")),
			data={"data": json.dumps(doc)})

	async def simult_bulk_insert(self, docs, docs_per_conn=200):
		'''Insert multiple documents to the remote server using multiple connections,
		useful for big numbers
		:param docs: List of dict or Document objects to be inserted in all requests
		:param num_cons: Number of simultaneous connections to open to the server each time (default 10)
		:param docs_per_conn: Number of documents to insert per each connection (default 200)
		'''
		num_docs = len(docs)  # total number of docs passed
		tasks = []
		for i in range(0, num_docs, docs_per_conn):
			tasks.append(self.insert_many(docs[i:i+docs_per_conn]))

		return await asyncio.gather(*tasks)

	async def insert_many(self, docs):
		'''Insert multiple documents to the remote server

		:param docs: List of dict or Document objects to be inserted in one request'''
		return await self.session.post(self.url, json={
			"cmd": "frappe.client.insert_many",
			"docs": json.dumps(docs)
		})

	async def update(self, doc):
		'''Update a remote document

		:param doc: dict or Document object to be updated remotely. `name` is mandatory for this'''
		url = self.url + "/api/resource/" + quote(doc.get("doctype")) + "/" + quote(doc.get("name"))
		return self.post_process(self.session.put(url, json={"data": json.dumps(doc)}))
		#return self.post_process(res)

	async def bulk_update(self, docs):
			'''Bulk update documents remotely
			:param docs: List of dict or Document objects to be updated remotely (by `name`)'''
			return await self.session.post(self.url, json={
				'cmd': 'frappe.client.bulk_update',
				'docs': json.dumps(docs)
			})

	# def post_request(self, data):
	# 	res = self.session.post(self.url, json=data)
	# 	res = self.post_process(res)
	# 	return res

	# def preprocess(self, params):
	# 	'''convert dicts, lists to json'''
	# 	for key, value in params.items():
	# 		if isinstance(value, (dict, list)):
	# 			params[key] = json.dumps(value)
	#
	# 	return params

	async def post_process(self, response):
		try:
			rjson = await response.json()
		except ValueError:
			print(response.text)
			raise

		if rjson and ('exc' in rjson) and rjson['exc']:
			raise Exception(rjson['exc'])
		if 'message' in rjson:
			return rjson['message']
		elif 'data' in rjson:
			return rjson['data']
		else:
			return None

	# def __del__(self):
	# 	loop = asyncio.get_event_loop()
	# 	loop.run_until_complete(self.session.close())