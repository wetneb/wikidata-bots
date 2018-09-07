# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from org.wikidata.wdtk.datamodel.helpers import Datamodel
from org.wikidata.wdtk.datamodel.interfaces import PropertyIdValue
from org.wikidata.wdtk.datamodel.interfaces import StatementRank
from org.wikidata.wdtk.wikibaseapi import ApiConnection
from org.wikidata.wdtk.wikibaseapi import LoginFailedException
from org.wikidata.wdtk.wikibaseapi import WikibaseDataEditor
from org.wikidata.wdtk.wikibaseapi import WikibaseDataFetcher
from org.wikidata.wdtk.datamodel.json.jackson import JacksonDatatypeId
from java.lang import NumberFormatException
from java.math import BigDecimal

username = open('wikidata_username.txt', 'r').read().strip()
password = open('wikidata_password.txt', 'r').read().strip()

conn = ApiConnection.getWikidataApiConnection()
conn.login(username, password)
fetcher = WikibaseDataFetcher(conn, Datamodel.SITE_WIKIDATA)
editor = WikibaseDataEditor(conn, Datamodel.SITE_WIKIDATA);

import requests
import mwparserfromhell
from mwparserfromhell.nodes.heading import Heading
from mwparserfromhell.nodes.template import Template
import re
from datetime import datetime
from collections import defaultdict
from time import sleep
from unidecode import unidecode

requests_session = requests.Session()
requests_cookies = {}

PROPERTY_PROPOSAL_PREFIX = 'Wikidata:Property_proposal/'
QID_RE = re.compile('\{\{ *Q *\| *Q?(\d+) *\}\}', flags=re.IGNORECASE)
BARE_ENTITY_ID_RE = re.compile('(Q|P)(\d+)', flags=re.IGNORECASE)
PID_RE = re.compile('\{\{ *P\+? *\| *P?(\d+) *\}\}', flags=re.IGNORECASE)
UNICODE_ARROW = '→'

current_references = []

def cleanup_text(txt):
    # return unidecode(txt)
    return txt

def to_qid(s):
    m = QID_RE.match(s)
    if m:
        return m.group

def mks_str(subject, prop_id, s):
    value = Datamodel.makeStringValue(s)
    return mks(subject, prop_id, value)

def mks_item(subject, prop_id, qid, qualifiers=[]):
    value = Datamodel.makeWikidataItemIdValue(qid)
    return mks(subject, prop_id, value, qualifiers)

def mks_prop(subject, prop_id, pid):
    value = Datamodel.makeWikidataPropertyIdValue(pid)
    return mks(subject, prop_id, value)

def mks(subject, prop_id, value, qualifiers=[]):
    pid = Datamodel.makeWikidataPropertyIdValue(prop_id)
    claim = Datamodel.makeClaim(
        subject,
        Datamodel.makeValueSnak(
            pid, value),
        qualifiers)
    return Datamodel.makeStatement(claim, current_references, StatementRank.NORMAL, "")

def snak(prop_id, val):
    return Datamodel.makeSnakGroup([
        Datamodel.makeValueSnak(
            Datamodel.makeWikidataPropertyIdValue(prop_id),
            val)
    ])

def snak_item(prop_id, val_id):
    return snak(prop_id, Datamodel.makeWikidataItemIdValue(val_id))

def make_statementgroups(statements):
    dct = defaultdict(list)
    for statement in statements:
        dct[statement.getClaim().getMainSnak().getPropertyId()].append(statement)
    return [
        Datamodel.makeStatementGroup(lst)
        for lst in dct.values()
    ]

class ProposalReader(object):

    def __init__(self):
        self.subject_item = None
        self.datatype = None
        self.latest_labels = {}
        self.descriptions = {}
        self.allowed_values = None
        self.allowed_units = None
        self.domain = None
        self.formatter_url = None
        self.examples = []
        self.see_also = []
        self.country = None
        self.page_name = None
        self.topic = None
        self.source = None
        self.status = None
        self.lastrevid = None
        self.completeness = None
        self.orig_wikicode = None
        self.orig_template = None
        self.number_of_ids = None
        self.mixnmatch = None

    def check_proposal(self):
        if self.status != 'ready':
            raise ValueError('Proposal is not ready!')
        if self.datatype == 'external-id':
            if not self.examples:
                print('\n\nNO EXAMPLE PROVIDED!!!!!\n\n')
                raw_input('continue_anyway')
            fmt = self.allowed_values
            if not fmt or fmt.lower() == 'string':
                self.allowed_values = None
                print('No format provided for external-id')
                #raise ValueError('No format provided for external-id')
            else:
                fmt = fmt.strip()
                if fmt.startswith('<code>') and fmt.endswith('</code>'):
                    fmt = fmt[len('<code>'):-len('</code>')]
                if fmt.startswith('<nowiki>') and fmt.endswith('</nowiki>'):
                    fmt = fmt[len('<nowiki>'):-len('</nowiki>')]
                self.allowed_values = fmt
                print('REGEX: '+fmt)
                r = re.compile(fmt)
                for subject, target in self.examples:
                    m = r.match(target.getString())
                    if not m:
                        raise ValueError('Example value {} does not match format'.format(target))

            # Check for duplicates
            print()
            print('## Similar properties')
            self.similar_pids = list(self.find_similar_properties())
            self.see_also = set(list(self.see_also) + self.similar_pids)
            print()

    def initial_creation(self):
        global current_references
        self.output = ""
        npid = PropertyIdValue.NULL
        statements = []
        labels = []
        descriptions = []
        ref_pid = Datamodel.makeWikidataPropertyIdValue('P4656')
        ref_url = Datamodel.makeStringValue(self.proposal_permalink())
        ref_snak = Datamodel.makeValueSnak(ref_pid, ref_url)
        reference = Datamodel.makeReference([Datamodel.makeSnakGroup([ref_snak])])
        current_references = [reference]

        for lang, val in self.latest_labels.items():
            if valid_lang_code(lang):
                labels.append(Datamodel.makeMonolingualTextValue(val, lang))

        for lang, val in self.descriptions.items():
            if valid_lang_code(lang):
                descriptions.append(Datamodel.makeMonolingualTextValue(val, lang))

        # Type
        if self.datatype == 'external-id' and self.domain == 'Q5':
            statements.append(mks_item(npid, 'P31', 'Q19595382')) # wikidata property for authority control for people
        elif self.datatype == 'external-id':
            statements.append(mks_item(npid, 'P31', 'Q19847637')) # wikidata property for an identifier
        else:
            statements.append(mks_item(npid, 'P31', 'Q18616576')) # wikidata property

        # Subject item
        if self.subject_item:
            statements.append(mks_item(npid, 'P1629', self.subject_item))

        # Domain
        if self.domain and self.domain.startswith('Q'):
            statements.append(mks_item(npid, 'P2302', 'Q21503250', [
                snak_item('P2309', 'Q21503252'),
                snak_item('P2308', self.domain),
            ]))

        # Source website
        if self.source:
            for url in self.source.split(', '):
                statements.append(mks_str(npid, 'P1896', url))

        # Proposal discussion
        statements.append(mks_str(npid, 'P3254', 'https://www.wikidata.org/wiki/{}{}'.format(
                PROPERTY_PROPOSAL_PREFIX,
                self.page_name.replace(' ','_'))))

        # Formatter URL
        if self.formatter_url:
            statements.append(mks_str(npid, 'P1630', self.formatter_url))

        # Country
        if self.country:
            statements.append(mks_item(npid, 'P17', self.country))

        # Mix'n'match
        if self.mixnmatch:
            statements.append(mks_str(npid, 'P2264', self.mixnmatch))

        # Constraints
        if self.datatype == 'external-id':
            statements.append(mks_item(npid, 'P2302', 'Q19474404')) # single value constraint
            statements.append(mks_item(npid, 'P2302', 'Q21502410')) # distinct values constraint
            if self.allowed_values:
                statements.append(mks_str(npid, 'P1793', self.allowed_values))
                statements.append(mks_item(npid, 'P2302', 'Q21502404', [
                    snak('P1793', Datamodel.makeStringValue(self.allowed_values))
                ]))
        elif self.datatype == 'item':
            value_type_qid = self.parse_entity_id(self.allowed_values) if self.allowed_values else None
            if value_type_qid:
                statements.append(mks_item(npid, 'P2302', 'Q21510865', [
                    snak_item('P2309', 'Q21503252'),
                    snak_item('P2308', value_type_qid)
                ]))
        elif self.datatype == 'number':
            statements.append(mks_item(npid, 'P2302', 'Q52848401'))

        # Allowed units
        if self.datatype == 'quantity' or self.datatype == 'number' and self.allowed_units:
            print('ALLOWED UNITS')
            print(self.allowed_units)
            statements.append(mks_item(npid, 'P2302', 'Q21514353', [
                    snak_item('P2305', unit)
                    for unit in self.allowed_units]))

        # See also
        for see_also_pid in self.see_also or []:
            statements.append(mks_prop(npid, 'P1659', see_also_pid))

        # Expected completeness
        if self.completeness:
            statements.append(mks_item(npid, 'P2429', self.completeness))

        if self.number_of_ids:
            try:
                cleaned = BigDecimal(int(self.number_of_ids.replace(',','')))
                curdate = datetime.now()
                curmonth = Datamodel.makeTimeValue(curdate.year,
                    curdate.month,
                    1, 0, 0, 0, 10, 0,0,0, "http://www.wikidata.org/entity/Q1985727")
                statements.append(mks(npid, 'P4876',
                    Datamodel.makeQuantityValue(cleaned),
                    [snak('P585', curmonth)]))

            except ValueError:
                pass


        statement_groups = make_statementgroups(statements)
        if self.datatype == 'item':
            self.datatype = 'wikibase-item'
        if self.datatype == 'number':
            self.datatype = 'quantity'
        translated_datatype = JacksonDatatypeId.getDatatypeIriFromJsonDatatype(self.datatype)
        print(self.datatype)
        datatype_value = Datamodel.makeDatatypeIdValue(translated_datatype)
        propdoc = Datamodel.makePropertyDocument(PropertyIdValue.NULL,
            labels, descriptions, [],
            statement_groups, datatype_value)

        propdoc = editor.createPropertyDocument(propdoc, "creating property")
        return propdoc.getPropertyId()

    def subsequent_statements(self, pid):
        """
        returns all the statements that need to be
        made after the property is created
        """
        statements = defaultdict(list)

        # Subject item
        if self.subject_item:
            obj = Datamodel.makeWikidataItemIdValue(self.subject_item)
            statements[obj].append(
                mks(obj, 'P1687', pid)
            )

        # See also
        for see_also_pid in self.see_also or []:
            obj = Datamodel.makeWikidataPropertyIdValue(see_also_pid)
            statements[obj].append(
                mks(obj, 'P1659', pid)
            )

        # Examples
        for subject, target in self.examples or []:
            statements[pid].append(mks_item(pid, 'P1855', subject, [
                snak(pid.getId(), target) ]))
            subject_qid = Datamodel.makeWikidataItemIdValue(subject)
            statements[subject_qid].append(mks(
                subject_qid, pid.getId(), target))

        for subject, statements in statements.items():
            editor.updateStatements(subject, statements, [], 'create property')

    def to_template_doc(self):
        doc = """Property documentation
|topic = {}
""".format(self.topic)
        return "{{"+doc+"}}"

    def generate_ping(self, users):
        if not users:
            return ""
        else:
            return "{{Ping|"+"|".join(users[:6])+"}} " + self.generate_ping(users[6:])

    def to_notification(self, pid):
        ping = self.generate_ping(self.users) + " {{done}}: {{P|"+pid+"}}. − ~~~~"
        return ping

    def parse_proposal_page(self, page_name):
        """
        Parses a proposal page to extract metadata about the property to create.

        :param text: the name of the proposal page
        """
        self.page_name = page_name
        text = self.get_page_over_api(PROPERTY_PROPOSAL_PREFIX+page_name)
        wikicode = mwparserfromhell.parse(cleanup_text(text.encode('utf-8')))

        for node in wikicode.filter(forcetype=(Template,Heading)):
            if isinstance(node, Heading):
                self.latest_labels = self.parse_translatable(node.title)
            elif isinstance(node, Template):
                template = node
                if (unicode(template.name).strip() == 'Property proposal' and
                    template.get('status').value.strip() == 'ready'):
                    self.parse_proposal_template(template)
                    self.users = self.extract_users(wikicode)
                    break
        self.orig_wikicode = wikicode

    def update_proposal_and_doc(self, pid):
        for param in self.orig_template.params:
            if param.name.strip() == 'status':
                param.value = ' '+pid[1:]+'\n'
        new_text = unicode(self.orig_wikicode)+'\n'+self.to_notification(pid)

        edit_wiki_page('Property talk:'+pid, self.to_template_doc(), 'create')

        print(PROPERTY_PROPOSAL_PREFIX+self.page_name)
        edit_wiki_page(PROPERTY_PROPOSAL_PREFIX+self.page_name, new_text,
            'created at [[Property:{}|{}]]'.format(pid,pid))

    def wikicode_to_str(self, wikicode):
        s = unicode(wikicode)
        r = re.compile('<!--.*-->')
        s = r.sub('', s).strip()
        return s

    def parse_proposal_template(self, template):
        for param in template.params:
            key = param.name.strip()
            value = self.wikicode_to_str(param.value)
            if not value:
                continue

            if key == 'status':
                self.status = value
                print('STATUS: {}'.format(value))
            elif key == 'datatype':
                if value.lower() == 'external identifier' or value.lower() == 'external id':
                    value = 'external-id'
                self.datatype = value.lower()
                print('DATATYPE: {}'.format(value))
            elif key == 'description':
                self.descriptions = self.parse_translatable(param.value)
                print('DESC: {}'.format(str(self.descriptions)))
            elif key == 'subject item':
                self.subject_item = self.parse_entity_id(value)
                print('SUBJECT: {}'.format(self.subject_item))
            elif key == 'allowed values':
                if value.lower() == 'number' or value.lower() == 'numeric':
                    value = '[1-9]\d*'
                self.allowed_values = self.parse_entity_id(value) or value
                print('ALLOWED: {}'.format(self.allowed_values))
            elif key == 'allowed units':
                lst = set(value.split(',') + value.split('*'))
                qids = map(self.parse_entity_id, lst)
                self.allowed_units = [qid for qid in qids if qid and qid.startswith('Q')]
            elif key == 'example':
                raw_examples = unicode(value).split('*')
                self.examples = []
                for example in raw_examples:
                    self.parse_raw_example(example)
            elif key.startswith('example '):
                self.parse_raw_example(unicode(value))
            elif key == 'see also':
                lst = set(value.split(',') + value.split('*'))
                pids = map(self.parse_entity_id, lst)
                self.see_also = [pid for pid in pids if pid and pid.startswith('P')]
                print('SEE ALSO')
                print(self.see_also)
            elif key == 'country':
                self.country = self.parse_entity_id(value)
            elif key == 'formatter URL':
                self.formatter_url = value
                print('FORMATTER: {}'.format(value))
            elif key == 'topic':
                self.topic = value
            elif key == 'domain':
                self.domain = self.parse_entity_id(value)
            elif key == 'source':
                if value.startswith('http'):
                    self.source = value
            elif key == 'expected completeness':
                self.completeness = self.parse_entity_id(value)
            elif key == 'number of ids':
                self.number_of_ids = self.parse_number_of_ids(unicode(value))
            elif key == "mix'n'match":
                self.mixnmatch = unicode(value)
            else:
                print('Ignoring key: '+key)

        self.orig_template = template

    def parse_raw_example(self, example):
        if UNICODE_ARROW in example:
            parts = example.split(UNICODE_ARROW)
        else:
            parts = example.split('->')
        print('Example parts')
        print(parts)
        if len(parts) == 2:
            subject_qid = self.parse_entity_id(parts[0])
            target = self.parse_example_target(parts[1])
            if not subject_qid or not target:
                return
            print(target)
            self.examples.append((subject_qid,target))

    def parse_example_target(self, target):
        parsed = self.parse_entity_id(target)
        if parsed:
            return Datamodel.makeWikidataItemIdValue(parsed)
        r = re.compile('[± ]+')

        if self.datatype == 'quantity' or self.datatype == 'number':
            try:
                parts = [p.strip() for p in r.split(target) if p.strip()]
                print(parts)
                amount = BigDecimal(parts[0])
                precision = 0
                unit = ""
                if len(parts) > 1:
                    unit_qid = self.parse_entity_id(parts[-1])
                    if unit_qid:
                        unit = Datamodel.makeWikidataItemIdValue(unit_qid).getIri()
                    try:
                        precision = BigDecimal(parts[1])
                    except NumberFormatException:
                        pass
                if precision:
                    return Datamodel.makeQuantityValue(amount, amount-precision, amount+precision, unit)
                else:
                    return Datamodel.makeQuantityValue(amount, unit)
            except NumberFormatException as e:
                print(e)

        if target.strip().startswith('['):
            wiki = mwparserfromhell.parse(target)
            for extlink in wiki.filter_external_links():
                return Datamodel.makeStringValue(unicode(extlink.title))

        cleantarget = target.strip()
        if cleantarget.startswith('"') and cleantarget.endswith('"'):
            return Datamodel.makeStringValue(cleantarget[1:-1])
        elif self.datatype == 'string' or self.datatype == 'external-id':
            return Datamodel.makeStringValue(target.strip())

    def parse_number_of_ids(self, value):
        quantity_re = re.compile('\s*((?:[-+]\s*)?(?:[\d,]+\.\d*|\.?\d+)(?:[eE][-+]?\d+)?)\s*(?:([~!])|(?:\+/?-|±)\s*((?:[-+]\s*)?(?:[\d,]+\.\d*|\.?\d+)(?:[eE][-+]?\d+)?)|)\s*')
        m = quantity_re.match(value)
        if m:
            return value.strip()

        if value.strip().startswith('['):
            wiki = mwparserfromhell.parse(value)
            for extlink in wiki.filter_external_links():
                return self.parse_number_of_ids(str(extlink.title))

    def parse_translatable(self, wikicode):
        dct = {}
        for template in wikicode.filter_templates():
            if str(template.name).strip() == 'TranslateThis':
                for param in template.params:
                    lng = param.name.strip()
                    if lng != 'anchor':
                        dct[lng] = self.wikicode_to_str(param.value)
        return dct

    def parse_entity_id(self, value):
        s = value.strip()
        match = QID_RE.match(s)
        if match:
            return 'Q'+str(match.group(1))
        match = PID_RE.match(s)
        if match:
            return 'P'+str(match.group(1))
        match = BARE_ENTITY_ID_RE.match(s)
        if match:
            return s

    def proposal_permalink(self):
        return 'https://www.wikidata.org/w/index.php?title={}{}&oldid={}'.format(
            PROPERTY_PROPOSAL_PREFIX,
            self.page_name.replace(' ','_'),
            self.lastrevid)

    def extract_users(self, wikicode):
        users = set()
        for link in wikicode.filter_wikilinks():
            if link.title.startswith('User talk:'):
                users.add(unicode(link.title)[len('User talk:'):])
        return list(users)

    def get_page_over_api(self, page_name):
        r = requests.get('https://www.wikidata.org/w/api.php', params={
            'action':'query',
            'titles':page_name,
            'prop':'revisions',
            'rvprop':'ids|content',
            'format':'json',},
            headers={'User-Agent':'PropertyCreator 0.1'})
        r.raise_for_status()
        js = r.json()
        page = list(js.get('query',{}).get('pages',{}).values())[0]
        pagid = page.get('pageid', -1)
        if pagid == -1:
            raise ValueError("Invalid page.")
        revision = page.get('revisions',[{}])[0]
        self.lastrevid = revision.get('revid')
        text = revision.get('*')
        return text

    def extract_domain(self, url):
        return urlsplit(url).netloc

    def find_similar_properties(self):
        return [] # bypassed for now (find a way to import urlsplit)

        # 1 / extract the domain name of the formatter URL and source website
        #domains = []
        #if self.formatter_url:
        #    domains.append(self.extract_domain(self.formatter_url))
        #if self.source:
        #    domains.append(self.extract_domain(self.source))

        # 2 / query to find similar websites
        #for domain in domains:
        #    for pid in self.property_by_domain(domain):
        #        yield pid

    def property_by_domain(self, domain):
        query = ("""
        SELECT DISTINCT ?prop ?propLabel ?url WHERE {
        ?prop wdt:P31/wdt:P279* wd:Q18616576 ;
                (wdt:P1630 | wdt:P1896) ?url.
        FILTER(CONTAINS(?url, "%s"))
        SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
        }
        LIMIT 10
        """ % domain)
        r = requests.post('https://query.wikidata.org/sparql', {'query':query}, headers={'Accept':'application/json'})
        results = r.json()['results']['bindings']
        for result in results:
            print('\t'.join([ result[key]['value'] for key in ['prop', 'propLabel', 'url'] ]))
            pid = result['prop']['value'][len('http://www.wikidata.org/entity/'):]
            yield pid


def get_api_token(typ='csrf'):
    global requests_cookies, requests_session
    r = requests_session.get('https://www.wikidata.org/w/api.php', params={
        'action':'query',
        'meta':'tokens',
        'format': 'json',
        'type':typ
    }, cookies=requests_cookies)
    r.raise_for_status()
    token = r.json()['query']['tokens'][typ+'token']
    print(r.json())
    requests_cookies = r.cookies
    print(requests_cookies)
    return token

def login_to_edit(username, password):
    global requests_session, requests_cookies
    token = get_api_token('login')
    data = {
        'format':'json',
        'action':'login',
        'lgname':username,
        'lgpassword':password,
        'lgtoken':token,
    }
    r = requests_session.post(
        'https://www.wikidata.org/w/api.php',
        data=data,
        cookies=requests_cookies
    )
    print(r.json())
    sleep(1)
    requests_cookies = requests_session.cookies

def edit_wiki_page(page_name, content, summary=None, bot=False):
    global requests_session, requests_cookies

    # Get token
    token = get_api_token()

    data = {
    'action':'edit',
        'title': page_name,
        'text': content,
        'summary': summary,
        'format': 'json',
        'token': token,
        'watchlist': 'unwatch',
    }
    if bot:
        data['bot'] = '1'
    r = requests_session.post('https://www.wikidata.org/w/api.php', data=data, cookies=requests_cookies)
    requests_cookies = r.cookies
    print(r.json())
    r.raise_for_status()

def valid_lang_code(code):
    valid_codes =  [
      'aa', 'ab', 'abs', 'ace', 'ady', 'ady-cyrl', 'aeb', 'aeb-arab', 'aeb-latn', 'af', 'ak', 'aln', 'als', 'am', 'an', 'ang', 'anp', 'ar', 'arc', 'arn', 'arq', 'ary', 'arz', 'as', 'ase', 'ast', 'atj', 'av', 'avk', 'awa', 'ay', 'az', 'azb', 'ba', 'ban',
'bar', 'bat-smg', 'bbc', 'bbc-latn', 'bcc', 'bcl', 'be', 'be-tarask', 'be-x-old', 'bg', 'bgn', 'bh',
'bho', 'bi', 'bjn', 'bm', 'bn', 'bo', 'bpy', 'bqi', 'br', 'brh', 'bs', 'btm', 'bto', 'bug', 'bxr', 'ca', 'cbk-zam', 'cdo', 'ce', 'ceb', 'ch', 'cho', 'chr', 'chy', 'ckb', 'co', 'cps', 'cr', 'crh', 'crh-cyrl', 'crh-latn', 'cs', 'csb', 'cu', 'cv', 'cy', 'da',
'de', 'de-at', 'de-ch', 'de-formal', 'din', 'diq', 'dsb', 'dtp', 'dty', 'dv', 'dz', 'ee', 'egl',
'el', 'eml', 'en', 'en-ca', 'en-gb', 'eo', 'es', 'es-419', 'es-formal', 'et', 'eu', 'ext', 'fa', 'ff', 'fi', 'fit', 'fiu-vro', 'fj', 'fo', 'fr', 'frc', 'frp', 'frr', 'fur', 'fy', 'ga', 'gag', 'gan', 'gan-hans', 'gan-hant', 'gcr', 'gd', 'gl', 'glk', 'gn',
'gom', 'gom-deva', 'gom-latn', 'gor', 'got', 'grc', 'gsw', 'gu', 'gv', 'ha', 'hak', 'haw', 'he',
'hi', 'hif', 'hif-latn', 'hil', 'ho', 'hr', 'hrx', 'hsb', 'ht', 'hu', 'hu-formal', 'hy', 'hz', 'ia', 'id', 'ie', 'ig', 'ii', 'ik', 'ike-cans', 'ike-latn', 'ilo', 'inh', 'io', 'is', 'it', 'iu', 'ja', 'jam', 'jbo', 'jut', 'jv', 'ka', 'kaa', 'kab', 'kbd',
'kbd-cyrl', 'kbp', 'kea', 'kg', 'khw', 'ki', 'kiu', 'kj', 'kk', 'kk-arab', 'kk-cn', 'kk-cyrl',
'kk-kz', 'kk-latn', 'kk-tr', 'kl', 'km', 'kn', 'ko', 'ko-kp', 'koi', 'kr', 'krc', 'kri', 'krj', 'krl', 'ks', 'ks-arab', 'ks-deva', 'ksh', 'ku', 'ku-arab', 'ku-latn', 'kum', 'kv', 'kw', 'ky', 'la', 'lad', 'lb', 'lbe', 'lez', 'lfn', 'lg', 'li', 'lij', 'liv',
'lki', 'lmo', 'ln', 'lo', 'loz', 'lrc', 'lt', 'ltg', 'lus', 'luz', 'lv', 'lzh', 'lzz', 'mai',
'map-bms', 'mdf', 'mg', 'mh', 'mhr', 'mi', 'min', 'mk', 'ml', 'mn', 'mni', 'mo', 'mr', 'mrj', 'ms', 'mt', 'mus', 'mwl', 'my', 'myv', 'mzn', 'na', 'nah', 'nan', 'nap', 'nb', 'nds', 'nds-nl', 'ne', 'new', 'ng', 'niu', 'nl', 'nl-informal', 'nn', 'no', 'nod',
'nov', 'nrm', 'nso', 'nv', 'ny', 'nys', 'oc', 'olo', 'om', 'or', 'os', 'ota', 'pa', 'pag', 'pam', 'pap',
'pcd', 'pdc', 'pdt', 'pfl', 'pi', 'pih', 'pl', 'pms', 'pnb', 'pnt', 'prg', 'ps', 'pt', 'pt-br', 'qu', 'qug', 'rgn', 'rif', 'rm', 'rmy', 'rn', 'ro', 'roa-rup', 'roa-tara', 'ru', 'rue', 'rup', 'ruq', 'ruq-cyrl', 'ruq-latn', 'rw', 'rwr', 'sa', 'sah', 'sat',
'sc', 'scn', 'sco', 'sd', 'sdc', 'sdh', 'se', 'sei', 'ses', 'sg', 'sgs', 'sh', 'shi', 'shi-latn',
'shi-tfng', 'shn', 'shy-latn', 'si', 'simple', 'sje', 'sk', 'skr', 'skr-arab', 'sl', 'sli', 'sm', 'sma', 'smj', 'sn', 'so', 'sq', 'sr', 'sr-ec', 'sr-el', 'srn', 'srq', 'ss', 'st', 'stq', 'sty', 'su', 'sv', 'sw', 'szl', 'ta', 'tay', 'tcy', 'te', 'tet',
'tg', 'tg-cyrl', 'tg-latn', 'th', 'ti', 'tk', 'tl', 'tly', 'tn', 'to', 'tpi', 'tr', 'tru', 'ts', 'tt',
'tt-cyrl', 'tt-latn', 'tum', 'tw', 'ty', 'tyv', 'tzm', 'udm', 'ug', 'ug-arab', 'ug-latn', 'uk', 'ur', 'uz', 'uz-cyrl', 'uz-latn', 've', 'vec', 'vep', 'vi', 'vls', 'vmf', 'vo', 'vot', 'vro', 'wa', 'war', 'wo', 'wuu', 'xal', 'xh', 'xmf', 'yi', 'yo', 'yue',
'za', 'zea', 'zgh', 'zh', 'zh-classical', 'zh-cn', 'zh-hans', 'zh-hant', 'zh-hk',
'zh-min-nan', 'zh-mo', 'zh-my', 'zh-sg', 'zh-tw', 'zh-yue', 'zu' ]
    return code in valid_codes

if __name__ == '__main__':
    import sys
    p = ProposalReader()
    p.parse_proposal_page(sys.argv[1].decode('utf-8'))

    p.check_proposal()
    login_to_edit(username, password)

    #pid = Datamodel.makeWikidataPropertyIdValue('P5348')
    pid = p.initial_creation()
    p.subsequent_statements(pid)

    print('--- Template doc ---')
    print(p.to_template_doc())

    print('--- Notification ---')
    print(p.to_notification(pid.getId()))

    p.update_proposal_and_doc(pid.getId())



