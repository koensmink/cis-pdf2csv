\
import re
from cis_pdf2csv.parser import RE_HEADER

def test_header_examples():
    assert RE_HEADER.match("1.1.1 (L1) Ensure 'Enforce password history' is set to '24 or more password(s)' (Automated)")
    assert RE_HEADER.match("2.2.3 (L1) Ensure 'Access this computer from the network' is set to 'Administrators' (MS only) (Automated)")
