import pathlib
import unittest

import sys
from collections import defaultdict
from prettytable import PrettyTable
import datetime
from datetime import date

# define possible values as global constant
VALID_VALUES = {"0": ["INDI", "HEAD", "TRLR", "NOTE", "FAM"],
                "1": ["NAME", "SEX", "BIRT", "DEAT", "FAMC", "FAMS", "MARR", "HUSB", "WIFE", "CHIL", "DIV"],
                "2": ["DATE"]}


class Gedcom:

    def __init__(self, file, pretty):

        self.file = file
        self.directory = pathlib.Path(__file__).parent
        self.output = ""
        self.userdata = defaultdict(dict)
        self.familydata = defaultdict(dict)
        self.tempdata = ""
        self.curr_id = ""
        self.ptUsers = PrettyTable()
        self.ptFamily = PrettyTable()
        if pretty.lower() == "y":
            self.bool_to_print = True
        elif pretty.lower() == "n":
            self.bool_to_print = False
        else:
            print("Invalid input for pretty table argument")

    def analyze(self):
        """
        Function to check if file is valid
        """

        if self.file.endswith("ged"):
            self.check_file(self.open_file())
            error = self.calc_data()
            return self.output, self.userdata, self.familydata, error
        else:
            return "Can only analyze gedcom files. Enter a file ending with .ged"

    def open_file(self):
        """
        Function to try and open the file
        :return: Returns lines in the file if file is valid
        """
        try:
            with open(self.file, 'r') as ged:
                lines = ged.readlines()
        except FileNotFoundError:
            print("{} Not found in {}".format(self.file, self.directory))
            sys.exit()
        return lines

    def check_file(self, read_lines):
        """
        Function to read input file line by line and generate output
        :param read_lines: list
        :return: output as string
        """

        for offset, line in enumerate(read_lines):
            line = line.strip()
            if line == "":  # if last line is reached, return output
                return self.output
            split_words = line.split(" ")
            len_split_words = len(split_words)
            if split_words[0] in ["0", "1", "2"]:
                self.parse_file(line, split_words, len_split_words, offset)
            else:
                return "Invalid line on {}".format(line)

    def parse_file(self, line, split_words, len_split_words, offset):

        if len_split_words > 3:  # if there is a big name or date, append it to a single value in list
            split_words[2] += " " + " ".join(split_words[3:])
        process_flow_dict = {"INDI": self.append2userdata, "FAM": self.append2familydata}
        if split_words[0] == "0":
            if split_words[2] in process_flow_dict:
                process_flow_dict[split_words[2]](split_words)
                return
        process_flow2_dict = {"NOTE": self.donothing, "HUSB": self.appendHusbWifedata, "WIFE": self.appendHusbWifedata,
                              "CHIL": self.appendChilddata, "FAM": self.donothing, "INDI": self.donothing}

        try:
            if split_words[1] not in VALID_VALUES[
                split_words[0]]:  # check if splitwords[1] which is the tag value is in the global dictionary
                if len_split_words < 3:  # if no, add N after tag
                    self.tempdata = split_words[1]
            else:  # if yes add Y after tag
                if len_split_words < 3:
                    self.tempdata = split_words[1]
                else:
                    if split_words[1] in process_flow2_dict:
                        process_flow2_dict[split_words[1]](split_words)
                        return
                    if split_words[0] == "2":
                        self.appendDates(split_words)
                        return
                    else:
                        self.userdata[self.curr_id][split_words[1]] = split_words[2]
        except KeyError:  # if invalid level value, throw eror
            print("Invalid line found on {}".format(offset + 1))

    def append2userdata(self, split_words):

        if self.userdata.__contains__(split_words[1]):
            raise RepetitiveID(
                "Repetitive individual ID {}".format(split_words[1]))  # Check unipue individual ID. Xiaopeng Yuan

        self.userdata[split_words[1]] = {}
        self.curr_id = split_words[1]

    def append2familydata(self, split_words):

        if self.familydata.__contains__(split_words[1]):
            raise RepetitiveID(
                "Repetitive family ID {}".format(split_words[1]))  # Check unipue family ID. Xiaopeng Yuan
        self.familydata[split_words[1]] = {}
        self.familydata[split_words[1]]["CHIL"] = []
        self.curr_id = split_words[1]

    def appendHusbWifedata(self, split_words):
        self.familydata[self.curr_id][split_words[1]] = split_words[2]

    def appendChilddata(self, split_words):
        self.familydata[self.curr_id][split_words[1]].append(split_words[2])

    def appendDates(self, split_words):

        if self.curr_id in self.userdata:
            self.userdata[self.curr_id][self.tempdata + split_words[1]] = split_words[2]
        elif split_words[1] == "DATE":
            husband = self.familydata[self.curr_id]["HUSB"]
            wife = self.familydata[self.curr_id]["WIFE"]
            self.userdata[husband][self.tempdata + split_words[1]] = split_words[2]
            self.userdata[wife][self.tempdata + split_words[1]] = split_words[2]

    def donothing(self, split_words):
        return

    def calc_data(self):
        for key in self.userdata:

            today = date.today()

            try:
                birthday = self.userdata[key]["BIRTDATE"]
                born_date = datetime.datetime.strptime(birthday, '%d %b %Y')
            except ValueError:
                print("Invalid date found")
                sys.exit()
            except KeyError:
                print(self.userdata[key])
                print("Invalid data for {}".format(self.userdata[key]))
                sys.exit()
            try:
                death_date = self.userdata[key]["DEATDATE"]
                deathday = self.userdata[key]["DEATDATE"]
                death_date = datetime.datetime.strptime(deathday, '%d %b %Y')
                alive_status = False
            except KeyError:
                alive_status = True
            self.userdata[key]["ALIVE"] = alive_status
            if alive_status is True:
                age = today.year - born_date.year
            else:
                age = death_date.year - born_date.year
            self.userdata[key]["AGE"] = age

            try:  # Check if marriage before 14, also add something to test cases.  Xiaopeng Yuan
                marriageday = self.userdata[key]["MARRDATE"]
            except KeyError:
                marriageday = "NA"

            if (marriageday != "NA" and (int(marriageday.split()[2]) - int(birthday.split()[2])) < 14):
                raise MarriageBefore14("{} Marriage before age 14".format(self.userdata[key]["NAME"]))

        error = self.prettyTablefunc()
        if error is None:
            error = "No errors found"
        return error

    def prettyTablefunc(self):

        self.ptUsers.field_names = ["ID", "NAME", "GENDER", "BIRTH DATE", "AGE", "ALIVE", "DEATH", "CHILD", "SPOUSE"]

        for key in sorted(self.userdata.keys()):
            value = self.userdata[key]
            name = value["NAME"]
            gender = value["SEX"]
            birthdate = value["BIRTDATE"]
            if birthdate == "08 DEC 1880":
                pass
            age = value["AGE"]
            alive = value["ALIVE"]
            single_list = []
            try:
                value["MARR"]
            except KeyError:
                single_list.append(value["NAME"])
            try:
                death = value["DEATDATE"]
            except KeyError:
                death = "NA"
            try:
                child = value["CHILD"]
            except KeyError:
                child = "NA"
            try:
                spouse = value["SPOUSE"]
            except KeyError:
                spouse = "NA"

            try:  # Check if marriage before 14, also add something to test cases.  Xiaopeng Yuan
                marriage = value["MARRDATE"]
            except KeyError:
                marriage = "NA"



            if death != "NA" and datetime.datetime.strptime(marriage, '%d %b %Y') > datetime.datetime.strptime(death,
                                                                                                               '%d %b %Y'):
                raise MarriageBeforeDeath("{} has Marriage before death".format(name))

            if (death == "NA" and age > 150):
                raise AgeMoreOnefifty("{} Age is more than 150".format(name))

            if marriage != "NA" and datetime.datetime.strptime(birthdate, '%d %b %Y') > datetime.datetime.strptime(marriage,
                                                                                                               '%d %b %Y'):
                raise BirthBeforeMarraige("{} has birth  after  marraige".format(name))


            self.ptUsers.add_row([key, name, gender, birthdate, age, alive, death, child, spouse])

        if self.bool_to_print:
            print(self.ptUsers)

        self.ptFamily.field_names = ["ID", "MARRIAGE DATE", "DIVORCE DATE", "HUSBAND ID", "HUSBAND NAME", "WIFE ID",
                                     "WIFE NAME", "CHILDREN"]

        for key in sorted(self.familydata.keys()):

            uniquenameslist = []

            value = self.familydata[key]

            husband_id = value["HUSB"]
            children = value["CHIL"]
            if len(children) > 5:
                raise SiblingGreaterThan5("Family {} has more than 5 siblings.".format(
                    key))  # Check if the family has more than 5 sidlings.     Xiaopeng Yuan
            husband_name = self.userdata[husband_id]["NAME"]
            husband_firstname, husband_lastname = husband_name.split()
            uniquenameslist.append(husband_firstname)
            try:
                marriage = self.userdata[husband_id]["MARRDATE"]
            except KeyError:
                return "No Marriage date found"
            wife_id = value["WIFE"]
            wife_name = self.userdata[wife_id]["NAME"]
            wife_firstname, wife_lastname = wife_name.split()
            if wife_firstname not in uniquenameslist:
                uniquenameslist.append(wife_firstname)
            else:
                raise UniqueFirstNames("{} and {} have same first names".format(husband_firstname, wife_firstname))
            try:
                divorce = self.userdata[husband_id]["DIVDATE"]
            except KeyError:
                divorce = "NA"

            for child in children:

                birthday = datetime.datetime.strptime(self.userdata[child]["BIRTDATE"], '%d %b %Y')
                child_name = self.userdata[child]["NAME"]
                child_firstname, child_lastname = child_name.split()

                if child_firstname not in uniquenameslist:
                    uniquenameslist.append(child_firstname)
                else:
                    raise UniqueFirstNames("{} does not have unique first name".format(child_firstname))

                for c in children:
                    if c != child:
                        c_birthday = datetime.datetime.strptime(self.userdata[c]["BIRTDATE"], '%d %b %Y')
                        if abs(birthday - c_birthday).days < 275 and abs(birthday - c_birthday).days > 2:
                            raise SiblingSpacing("Sibling {} and {} have invaild spacing.".format(child, c))

                if self.userdata[child]["SEX"] == "M":
                    child_firstname, child_lastname = self.userdata[child]["NAME"].split()
                    if child_lastname.strip("/") != husband_firstname:
                        raise MaleLastNames(
                            "Child {} and Father {} have different last names".format(self.userdata[child]["NAME"],
                                                                                      husband_name))

            if (divorce != "NA") and (datetime.datetime.strptime(divorce, '%d %b %Y') > datetime.datetime.strptime(
                    self.userdata[husband_id]["DEATDATE"], '%d %b %Y')):
                raise DivorceAfterDeathError("{} divorces after death".format(husband_name))

            if (divorce != "NA") and (datetime.datetime.strptime(marriage, '%d %b %Y') > datetime.datetime.strptime(divorce, '%d %b %Y')):
                raise MarriageBeforeDivorce("{} marraige after divorce".format(name))

            if "FAMC" in self.userdata[husband_id] and "FAMC" in self.userdata[wife_id]:
                if self.userdata[husband_id]["FAMC"] == self.userdata[wife_id]["FAMC"]:
                    raise SiblingMarriageError("{} and {} are siblings".format(husband_name, wife_name))

            if (divorce != "NA") and not (
                    self.userdata[husband_id]["SEX"] == "M" and self.userdata[wife_id]["SEX"] == "F"):
                raise GenderError("{} and {} are of same gender".format(husband_name, wife_name))




            try:
                child = value["CHIL"]
            except KeyError:
                child = "NA"
            self.ptFamily.add_row([key, marriage, divorce, husband_id, husband_name, wife_id, wife_name, child])

        if self.bool_to_print is True:
            print(self.ptFamily)


class DivorceAfterDeathError(Exception):
    """Raised when husb/wife divorce after their death"""
    pass


class SiblingMarriageError(Exception):
    """Raised when husb/wife divorce after their death"""
    pass


class AgeMoreOnefifty(Exception):
    pass


class MarriageBefore14(Exception):
    pass


class GenderError(Exception):
    pass


class RepetitiveID(Exception):
    pass


class MaleLastNames(Exception):
    pass


class SiblingGreaterThan5(Exception):
    pass


class SiblingSpacing(Exception):
    pass


class MarriageBeforeDeath(Exception):
    pass


class UniqueFirstNames(Exception):
    pass

class MarriageBeforeDivorce(Exception):
    pass

class BirthBeforeMarraige(Exception):
    pass


class TestCases(unittest.TestCase):

    def setUp(self):
        """
        Set up objects with filenames
        """
        self.x = Gedcom("proj03testDivorceAfterDeath.ged", "n")
        self.x1 = Gedcom("proj04testsiblingsmarriage.ged", "n")
        self.x2 = Gedcom("proj03testAgeLessOneFifty.ged", "n")
        self.x3 = Gedcom("proj04testCorrectGender.ged", "n")
        self.x4 = Gedcom("proj04testMarriagebefore14.ged", "n")
        self.x5 = Gedcom("proj04testUniqueID.ged", "n")
        self.x6 = Gedcom("proj04testmalelastnames.ged", "n")
        self.x7 = Gedcom("proj06testsiblingsgreaterthan5.ged", "n")
        self.x8 = Gedcom("proj06testsiblingspacing.ged", "n")
        self.x9 = Gedcom("proj06testmarriagebeforedeath.ged", "n")
        self.x10 = Gedcom("proj06testuniquefirstnames.ged", "n")
        self.x11 = Gedcom("proj06testmarraigebeforedivorce.ged", "n")
        self.x12 = Gedcom("proj06testbirthbeforemarraige.ged", "n")


    def test_divorceAfterDeath(self):
        """
        Test if hus/wife divorces after death
        """
        # self.assertRaises(DivorceAfterDeathError, lambda: self.x.analyze())

    def test_SiblingMarriage(self):
        """
        Test if siblings marry
        """
        # self.assertRaises(SiblingMarriageError, lambda: self.x1.analyze())

    def test_AgeLessOneFifty(self):
        """
        Test if siblings marry
        """
        self.assertRaises(AgeMoreOnefifty, lambda: self.x2.analyze())

    def test_ProperGender(self):
        """
        Test if siblings marry
        """
        self.assertRaises(GenderError, lambda: self.x3.analyze())

    def test_MarriageBefore14(self):
        """
        Test if marriage before 14
        """
        self.assertRaises(MarriageBefore14, lambda: self.x4.analyze())

    def test_RepetitiveID(self):
        """
        Test if ID is unique
        """
        self.assertRaises(RepetitiveID, lambda: self.x5.analyze())

    def test_malelastnames(self):
        """
        Test if male children have same last name in family
        """
        self.assertRaises(MaleLastNames, lambda: self.x6.analyze())

    def test_siblingsgreaterthan5(self):
        """
        Test if male children have same last name in family
        """
        self.assertRaises(SiblingGreaterThan5, lambda: self.x7.analyze())

    def test_siblingspacing(self):
        """
        Test if male children have same last name in family
        """
        self.assertRaises(SiblingSpacing, lambda: self.x8.analyze())

    def test_marriagebeforedeath(self):
        """
        Test if male children have same last name in family
        """
        self.assertRaises(MarriageBeforeDeath, lambda: self.x9.analyze())

    def test_uniquefirstnames(self):
        """
        Test if male children have same last name in family
        """
        self.assertRaises(UniqueFirstNames, lambda: self.x10.analyze())

    def test_uniquefirstnames(self):
        """
        Test if male children have same last name in family
        """
        self.assertRaises(UniqueFirstNames, lambda: self.x10.analyze())

    def test_marraigebeforedivorce(self):
        self.assertRaises(MarriageBeforeDivorce, lambda: self.x11.analyze())
        """
        Test if marraige date is before divorce date
        """


    def test_birthbeforemaaraige(self):
        self.assertRaises(BirthBeforeMarraige, lambda: self.x12.analyze())
        """
        Test if birth date is before marraige date
        """




def main():
    file = input("Enter file name: \n")
    pretty = input("Do you want pretty table? y/n \n")
    g = Gedcom(file, pretty)
    op, userdata, familydata, error = g.analyze()
    print(error)
    # print(op)
    # print(userdata)
    # print(familydata)


if __name__ == '__main__':
    unittest.main(exit=False, verbosity=2)
    main()
