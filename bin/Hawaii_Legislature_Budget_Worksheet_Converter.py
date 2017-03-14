#!/usr/bin/env python3
__author__ = "McKay H Davis"
__date__ = "2016-03-20Z20:08"
__copyright__ = "Copyright 2016"
__license__ = "GPLv3"
__version__ = "0.0.1"
__maintainer__ = "McKay Davis"
__email__ = "mckay@codeforhawaii.org"
__doc__ = """
Hawaii_Legislature_Budget_Worksheet_Converter.py:
Converts Hawaii State Legislature budget worksheets from PDF format to Tab-Separated-Values (TSV) format for import into a spreadsheet programs.
"""

PDFTOTEXT_FIXED_PARAM = 4

COL_END_SEQUENCE_NUM = 19
COL_BEG_EXPLANATION_NUM = 21
COL_END_EXPLANATION_PROGRAM = 62
COL_END_EXPLANATION_DEPT_SUMMARY = 46

COL_BEG_FY0_POS = 5
COL_END_FY0_POS = 16

COL_BEG_FY0_AMT = 18
COL_END_FY0_AMT = 33

COL_BEG_FY0_MOF = 35
COL_END_FY0_MOF = 35

COL_BEG_FY1_POS = 44
COL_END_FY1_POS = 55

COL_BEG_FY1_AMT = 57
COL_END_FY1_AMT = 72
COL_BEG_FY1_MOF = 73
COL_END_FY1_MOF = 76

SPECIAL_EXPLANATIONS = ["BASE APPROPRIATIONS",
                        "TOTAL BUDGET CHANGES",
                        "BUDGET TOTALS",
                        "DEPARTMENT APPROPRIATIONS",
                        "TOTAL DEPARTMENT APPROPRIATIONS",
                        "DEPARTMENT BUDGET CHANGES",
                        "TOTAL DEPARTMENT BUDGET CHANGES",
                        "DEPARTMENT TOTAL BUDGET",
                        "TOTAL DEPARTMENT BUDGET",
                        "TOTAL APPROPRIATIONS",
                        "GRAND TOTAL APPROPRIATIONS",
                        "TOTAL CHANGES",
                        "GRAND TOTAL CHANGES",
                        "GRAND TOTAL BUDGET"]

DESC_DEPT = {
    "Department of Agriculture (DOA)" : "AGR",
    "Department of Accounting and General Services (DAGS)" : "AGS",
    "Department of the Attorney General (AG)" : "ATG",
    "Department of Business, Economic Development, and Tourism (DBEDT)" : "BED",
    "Department of Budget and Finance (B&F)" : "BUF",
    "Department of Commerce and Consumer Affairs (DCCA)" : "CCA",
    "Department of Defense (DOD)" : "DEF",
    "Department of Education (DOE)" : "EDN",
    "Office of the Governor" : "GOV",
    "Department of Hawaiian Home Lands (DHHL)" : "HHL",
    "Department of Human Services (DHS)" : "HMS",
    "Department of Human Resources Development (DHRD) " : "HRD",
    "Department of Health (DOH)" : "HTH",
    "Judiciary" : "JUD",
    "Department of Labor and Industrial Relations (DLIR)" : "LBR",
    "Department of Land and Natural Resources (DLNR)" : "LNR",
    "Office of the Lieutenant Governor (LG)" : "LTG",
    "Department of Public Safety (DPS) " : "PSD",
    "Subsidies" : "SUB",
    "Department of Taxation (DOTAX)" : "TAX",
    "Department of Transportation (DOT)" : "TRN",
    "University of Hawaii (UH)" : "UOH",
    "City and County of Honolulu" : "CCH",
    "County of Hawaii" : "COH",
    "County of Kauai" : "COK",
    "County of Maui" : "COM"
}

DEPT_DESC = { v: k for k, v in DESC_DEPT.items() }


MOF = {
    "A" : "general funds",
    "B" : "special funds",
    "C" : "general obligation bond fund",
    "D" : "general obligation bond fund with debt service cost to be paid from special funds",
    "E" : "revenue bond funds",
    "J" : "federal aid interstate funds",
    "K" : "federal aid primary funds",
    "L" : "federal aid secondary funds",
    "M" : "federal aid urban funds",
    "N" : "federal funds",
    "P" : "other federal funds",
    "R" : "private contributions",
    "S" : "county funds",
    "T" : "trust funds",
    "U" : "interdepartmental transfers",
    "W" : "revolving funds",
    "X" : "other funds"
}



import subprocess
import sys
import getopt
import datetime
import re
import collections
import Spans








def err(txt):
    sys.stderr.write(">>> {}".format(txt))
    sys.stderr.write("\n");


def err_col(line):
    err("".join("{}".format((i//10)%10) for i in range(0,len (line))))
    err("".join("{}".format(i%10) for i in range(0,len (line))))
    err(line)


def main():
    csv = pdf_to_csv(sys.argv[1])
    f = open(sys.argv[1] + ".csv", "wb")
    f.write(csv)
    return 0


def pdf_to_csv(pdf_filename):
    text = pdftotext(pdf_filename)
    # split pages at pagebreak char
    textpages = text.split("\x0c")
    # remove last page, which is empty
    textpages = textpages[:-1]
    # create a HBWSPage instance for each page
    #pages = [ for pagetext in textpages]

    pages = []
    for pagetext in textpages:
        page = HBWSPage(pagetext)
        print(page.debug_str())
        pages.append(page)

        #[) for page in pages]

    return get_spreadsheet(pages, ",")

def get_spreadsheet(pages, delimiter="\t"):
    text = []
    header = True
    for page in pages:
        for row in page.get_spreadsheet_rows(header):
            header = False
            row = ["" if ent is None else ent for ent in row]
            row = ['"{}"'.format(ent) for ent in row]
            text.append(delimiter.join(row))
    return "\n".join(text)


def delchar_at_pos(txt, atpos):
    return txt[:atpos] + txt[atpos+1:]

def inschar_at_pos(txt, char, atpos):
    return txt[:atpos] + char + txt[atpos:]





PROGRAM_SEQUENCES_SPANS = Spans.Spans()
DEPARTMENT_SEQUENCES_SPANS = Spans.Spans()


class HBWSPage:
    """Hawaii Budget Worksheet Page"""
    def __init__(self, text):
        global PROGRAM_SEQUENCES_SPANS, DEPARTMENT_SEQUENCES_SPANS

        text = text.replace("*************************************************************************************",
                     "*" * 25)

        # split the page text into single lines
        self.text = text.split("\n")
        # split each line into components seperated by two or more spaces
        self.lines = [re.split(" \s+", line) for line in self.text]
        self.curline = 0

        self.parse_page_header_line0(self.getline())
        self.parse_page_header_line1(self.getline())
        self.eat_empty_lines()

        self.parse_department_or_program_id(self.getline())
        self.eat_empty_lines()


        if self.program_page:
            # Parse Program Page
            self.parse_structure_number(self.getline())
            self.parse_subject_committee(self.getline())
            self.eat_empty_lines()

            self.parse_program_table_header_line1(self.getline())
            self.parse_program_table_header_line2(self.getline())
            self.eat_empty_lines()

            # parse sequences step 1
            sequences = self.parse_sequences_step1(162)


            bug1 = self.pagenum == 52 and "6-001" in sequences

            bug2 = self.pagenum == 65 and "TOTAL BUDGET CHANGES" in sequences

            bug1 = bug2 = False

            if bug1:
                sequences["6-001"][-10] = delchar_at_pos(sequences["6-001"][-10], -20)
                sequences["6-001"][-10] = inschar_at_pos(sequences["6-001"][-10], " ", -1)

                sequences["6-001"][-8] = delchar_at_pos(sequences["6-001"][-8], -20)
                sequences["6-001"][-8] = inschar_at_pos(sequences["6-001"][-8], " ", -1)

                sequences["6-001"][-4] = sequences["6-001"][-4][:-1] + " N"
                sequences["6-001"][-2] = sequences["6-001"][-2][:-1] + " W"



            if bug2:
                sequences["TOTAL BUDGET CHANGES"][0] = delchar_at_pos(sequences["TOTAL BUDGET CHANGES"][0], -20)
                sequences["TOTAL BUDGET CHANGES"][0] = inschar_at_pos(sequences["TOTAL BUDGET CHANGES"][0], " ", -1)





            spans = self.parse_sequences_spans(sequences, bug1)

            if not len(PROGRAM_SEQUENCES_SPANS.ss):
                PROGRAM_SEQUENCES_SPANS = spans
            else:
                new_ss = PROGRAM_SEQUENCES_SPANS.union(spans)
                if spans.ss and spans.ss[-1][0] == 162:
                    self.print_sequences_spans(sequences, spans)
                    input("162 introduced on page {}".format(self.pagenum))

                if len(new_ss.ss) != len(PROGRAM_SEQUENCES_SPANS.ss):
                    err("\n{}: {}\n{}: {}\n\n{}: {}".format
                        (len(new_ss.ss), new_ss.ss,
                         len(PROGRAM_SEQUENCES_SPANS.ss), PROGRAM_SEQUENCES_SPANS.ss,
                         len(spans.ss), spans.ss))
                    self.print_sequences_spans(sequences, spans)
                    assert 0
                PROGRAM_SEQUENCES_SPANS = new_ss

            self.print_sequences_spans(sequences, PROGRAM_SEQUENCES_SPANS)


            # parse sequences step 2
            #self.parse_sequences_step2(sequences, COL_END_EXPLANATION_PROGRAM)
        else:
            assert self.department_summary_page

            line = self.getline()
            self.assert_linepos_is(line, 1, "EX")
            self.assert_linepos_is(line, 2, "FIRST FY")
            self.assert_linepos_is(line, 3, "SECOND FY")

            self.parse_program_table_header_line2(self.getline())

            self.eat_empty_lines()

            sequences = self.parse_sequences_step1()
            spans = self.parse_sequences_spans(sequences)


            if not len(DEPARTMENT_SEQUENCES_SPANS.ss):
                DEPARTMENT_SEQUENCES_SPANS = spans
            else:
                new_ss = DEPARTMENT_SEQUENCES_SPANS.union(spans)
                if len(new_ss.ss) != len(DEPARTMENT_SEQUENCES_SPANS.ss):
                    err("\n{}: {}\n{}: {}\n\n{}: {}".format(len(new_ss.ss), new_ss.ss, len(DEPARTMENT_SEQUENCES_SPANS.ss), DEPARTMENT_SEQUENCES_SPANS.ss, len(spans.ss), spans.ss))
                    self.print_sequences_spans(sequences, spans)
                    assert 0
                DEPARTMENT_SEQUENCES_SPANS = new_ss

            self.print_sequences_spans(sequences, DEPARTMENT_SEQUENCES_SPANS)
            #self.parse_sequences_step2(sequences, COL_END_EXPLANATION_DEPT_SUMMARY)

        #print(self.debug_str()+"\n")
        err("PROGRAM_SEQUENCES_SPANS")
        err(PROGRAM_SEQUENCES_SPANS.ss)


    def eat_empty_lines(self):
        while self.curline < len(self.lines) and self.lines[self.curline] == [""]: self.curline += 1

    def getline(self):
        self.curline += 1
        return self.lines[self.curline-1]

    def parse_sequences_step1(self, special_col = 0):
        special_explanations = SPECIAL_EXPLANATIONS

        seq_ids = [special_explanations[0]]
        sequences = collections.OrderedDict()
        sequences[seq_ids[-1]] = []

        for seqline in range(self.curline, len(self.text)):
            linetxt = self.text[seqline]

            seq_id = linetxt[:COL_END_SEQUENCE_NUM].strip()
            text = linetxt[COL_BEG_EXPLANATION_NUM:]

            if special_col and special_col < len(text) and text[special_col] != " ":
                text = inschar_at_pos(text, " ", 162)

            if not seq_id:
                for special in special_explanations:
                    if text.lstrip().startswith(special):
                        seq_id = special
                        break

            if len(seq_id) and not seq_id == seq_ids[-1]:
                sequences[seq_id] = []
                seq_ids.append(seq_id)

            seq_id = seq_ids[-1]
            sequences[seq_id].append(text)

        assert list(sorted(seq_ids)) == list(sorted(sequences.keys())), "{}\n{}\n".format(list(sorted(seq_ids)), list(sorted(sequences.keys())))
        return sequences

        return (seq_ids, sequences)


    def parse_sequences_spans(self, sequences, debug = False):
        spans = Spans.Spans()
        for seq, seq_lines in sequences.items():
            for i, seq_line in enumerate(seq_lines):
                err("-"*120)
                err("seq_line {}".format(i))
                err_col(seq_line)
                line_spans = Spans.Spans.from_text(seq_line)
                err(line_spans.ss)
                err(line_spans.extract_text(seq_line))
                spans = spans.union(line_spans)
                err(spans.extract_text(seq_line))
                err(spans.ss)
                err("-"*120)

        return spans

    def print_sequences_spans(self, sequences, spans):
        indent = max(len(seq) for seq in sequences.keys())
        for seq, seq_lines in sequences.items():
            for seq_line in seq_lines:
                parts = spans.extract_text(seq_line)
                err("\nseq: {:20s} ---> {}".format(seq, parts))


    def parse_sequences_with_spans(self, sequences, spans):
        self.explanations = {}
        self.line_items = {}
        self.seq_ids = []

        for seq_id, seq_lines in sequences.items():

            explanation, line_item = self.parse_sequence(seq_id, seq_lines, col_end_explanation)
            if explanation or line_item:
                self.explanations[seq_id] = explanation
                self.line_items[seq_id] = line_item
                self.seq_ids.append(seq_id)



    def parse_sequences_step2(self, sequences, col_end_explanation):
        self.explanations = {}
        self.line_items = {}
        self.seq_ids = []

        for seq_id, seq_lines in sequences.items():
            explanation, line_item = self.parse_sequence(seq_id, seq_lines, col_end_explanation)
            if explanation or line_item:
                self.explanations[seq_id] = explanation
                self.line_items[seq_id] = line_item
                self.seq_ids.append(seq_id)



    def parse_sequence(self, seq_id, lines, col_end_explanation):
        explanations = []
        line_items = []
        for line in lines:

            explanation = line[:col_end_explanation]
            #print("EXPLANATION FROM:'{}' TO '{}'".format(line, explanation))
            explanation = explanation.rstrip()
            if explanation.lstrip().startswith(seq_id): explanation = explanation.lstrip();
            if explanation: explanations.append(explanation)

            line = line[col_end_explanation:]
            err("parse sequence line:")
            err_col(line)

            line_item = self.parse_line_item(line)
            line_items.append(line_item)
            err(line_item)

        while len(line_items) > 1 and not "".join(line_items[-1]) and not "".join(line_items[-2]): line_items = line_items[:-1]
        while len(line_items) > 1 and not "".join(line_items[-1]): line_items = line_items[:-1]

        return (explanations, line_items)


    def parse_timestamp(self, line):
        # insert leading 0 for hour in time
        if line[2][1] == ":": line[2] = "0" + line[2]
        timestring = " ".join(line[1:3])
        timeformat = "%A, %B %d, %Y %H:%M:%S %p"
        return datetime.datetime.strptime(timestring, timeformat)

    def parse_pagenum(self, text):
        assert text[:5] == "Page "
        components = text[5:].split(" of ")
        assert len(components) == 2, "pagenum parsing failed to find ' of '"
        return (int(components[0]), int(components[1]))

    def assert_linepos_is(self, line, pos, isstr):
        assert line[pos].startswith(isstr), "position {} is not '{}', instead is '{}' -- entire line is: '{}' -- Page debug info: {}".format(pos, isstr, line[pos], "\t".join(line), self.debug_str())


    def parse_page_header_line0(self, line):
        self.assert_linepos_is(line, 3, "LEGISLATIVE BUDGET SYSTEM")
        self.datetime = self.parse_timestamp(line)
        self.pagenum, self.pages = self.parse_pagenum(line[4])

    def parse_page_header_line1(self, line):
        self.assert_linepos_is(line, 1, "Detail Type:")
        self.assert_linepos_is(line, 2, "BUDGET WORKSHEET")
        self.detail_type = line[1].split()[-1]

    def parse_department_or_program_id(self, line):
        self.department_summary_page = line[1] == "Department:"
        self.program_page = "Program ID" in line[1]

        assert self.program_page or self.department_summary_page

        if ((self.program_page and len(line) > 2 and len(line[2]) > 3) or
            (self.department_summary_page and len(line) > 2)):
            self.department_code = line[2][:3]
            self.department = DEPT_DESC[self.department_code]

        if self.program_page:
            self.program_id = int(line[2][3:])
            self.program_name = line[3]




    def parse_structure_number(self, line):
        if line[1].startswith("Subject Committee"):
            self.curline -= 1
            return

        self.assert_linepos_is(line, 1, "Structure #:")
        # Keeping as string to preserve leading zeros
        if len(line) == 2:
            self.structure_number = line[1].split()[-1]
        else:
            self.structure_number = line[2]

    def parse_subject_committee(self, line):
        assert line[1][:-3] == "Subject Committee: "
        self.subject_committee_code = line[1][-3:]
        self.subject_committee_name = line[2]

    def parse_program_table_header_line1(self, line):
        self.assert_linepos_is(line, 1, "SEQ #")
        self.assert_linepos_is(line, 2, "EXPLANATION")
        assert line[3][:-4] == "FY "
        assert line[4][:-4] == "FY "
        self.year0 = int(line[3][-4:])
        self.year1 = int(line[4][-4:])


    def parse_program_table_header_line2(self, line):
        assert len(line) == 7, line

        assert line[1] == "Perm", line
        assert line[2] == "Temp", line
        assert line[3] == "Amt", line

        assert line[4] == "Perm", line
        assert line[5] == "Temp", line
        assert line[6] == "Amt", line


    def debug_str(self):
        props = ["datetime", "pagenum", "pages", "detail_type", "department_code", "program_id", "program_name", "structure_number", "subject_committee_code", "subject_committee_name", "year0", "year1"]
        dstrs = []
        for prop in props:
            val = getattr(self, prop, None)
            #if not val is None:
            dstrs.append("{}={}".format(prop, val))

        seq_ids = getattr(self, "seq_ids", [])
        for seq_id in seq_ids:
            dstrs.append("")
            dstrs.append("Sequence ID={}".format(seq_id))
            dstrs.append("Explanation:")
            dstrs.append("\n".join(self.explanations[seq_id]))
            dstrs.append("Line Items:")
            dstrs.append(str(self.line_items[seq_id]))

        return "\n".join(dstrs)


    def get_spreadsheet_header(self):
        props = ["datetime", "pagenum", "pages", "year0", "year1", "detail_type", "department_code", "department", "program_id", "program_name", "structure_number", "subject_committee_code", "subject_committee_name", "sequence_num", "explanation", "pos_y0", "amt_y0", "mof_y0", "pos_y1", "amt_y1", "mof_y1",]
        return props


    def get_spreadsheet_rows(self, emit_header = False):
        props = self.get_spreadsheet_header()
        seq_ids = getattr(self, "seq_ids", [])
        rows = []
        row = [str(getattr(self, prop, "")) for prop in props]
        idxof = dict(zip(props, range(len(props))))
        for seq_id in seq_ids:
            row[idxof["sequence_num"]] = seq_id
            row[idxof["explanation"]] = "\n".join(self.explanations[seq_id])
            line_items = self.line_items[seq_id] if len(self.line_items[seq_id]) else [[None]*6]
            for line_item in line_items:
                row[idxof["pos_y0"]],row[idxof["amt_y0"]],row[idxof["mof_y0"]] = line_item[0:3]
                row[idxof["pos_y1"]],row[idxof["amt_y1"]],row[idxof["mof_y1"]] = line_item[3:6]
                rows.append(row[:])

        return [props] + rows if emit_header else rows



def pdftotext(pdf_filename):
    cmd = ["pdftotext",
           "-layout",
           "-fixed 4",
           '"'+pdf_filename+'"',
           "-"]
    buf = subprocess.check_output(" ".join(cmd), shell=True)
    text = buf.decode("utf-8")
    return text


if __name__ == "__main__":
    main()
