
class Transforms:
    _node_dbxref_to_codeid_exceptions = {
        'GO': (lambda sab, code: f"{sab} {sab}:{code}")
    }

    def _dbxref_to_codeid(self, sab: str, code: str) -> str:
        sab_uc = sab.upper()
        code_uc = code.upper()
        if sab_uc in self._node_dbxref_to_codeid_exceptions:
            return self._node_dbxref_to_codeid_exceptions[sab_uc](sab_uc, code_uc)
        return f"{sab_uc} {code_uc}"

    def file_from_uri(self, uri: str) -> str:
        if uri.find('/'):
            return uri.rsplit('/', 1)[1]

    def node_dbxref_to_codeid(self, node_dbxref: str) -> str:
        sab_code = node_dbxref.split(':')
        return self._dbxref_to_codeid(sab_code[0], sab_code[1])

    def node_id_to_codeid(self, node_id: str) -> str:
        file = self.file_from_uri(node_id)
        sab_code = file.split('_')
        return self._dbxref_to_codeid(sab_code[0], sab_code[1])

    def new_codeid_line_from_codeid(self, codeid: str) -> str:
        sab_code = codeid.split(' ')
        return f"\"{codeid}\",\"{sab_code[0]}\",\"{sab_code[1]}\""
