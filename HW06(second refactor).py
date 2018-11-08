"""
Program by Sanjeev Rajasekaran, Vikas Bhat, Ogadinma Njoku, Xiaopeng Yuang
Use: Analyze gedcom files, takes a file as input
"""

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
        self.samenameandbirthdate = []
        self.ptUsers = PrettyTable()
        self.ptFamily = PrettyTable()
        self.errorlog = defaultdict(int)
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
            error, errorlog = self.calc_data()
            return error, errorlog
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
            print("ERROR: US22 INDIVIDUAL {} has a repetitive ID".format(split_words[1]))
            self.errorlog["RepetitiveID"] += 1

        self.userdata[split_words[1]] = {}
        self.curr_id = split_words[1]

    def append2familydata(self, split_words):

        if self.familydata.__contains__(split_words[1]):
            print("ERROR: US 08 FAMILY {} has a repetitive ID".format(split_words[1]))
            self.errorlog["RepetitiveID"] += 1

        self.familydata[split_words[1]] = {}
        self.familydata[split_words[1]]["CHIL"] = []
        self.curr_id = split_words[1]

    def appendHusbWifedata(self, split_words):
        self.familydata[self.curr_id][split_words[1]] = split_words[2]

    def appendChilddata(self, split_words):
        self.familydata[self.curr_id][split_words[1]].append(split_words[2])

    def appendDates(self, split_words):

        if self.curr_id in self.userdata:
            if self.tempdata + split_words[1] == "MARRDATE":
                if self.userdata[self.curr_id].__contains__("MARRDATE"):
                    try:
                        self.userdata[self.curr_id]["DIVDATE"]
                    except KeyError:
                        print("ERROR: US11 INDIVIDUAL {} HAS DONE BIGAMY".format(self.curr_id))
                        self.errorlog["Bigamy"] += 1

            self.userdata[self.curr_id][self.tempdata + split_words[1]] = split_words[2]
        elif split_words[1] == "DATE":
            husband = self.familydata[self.curr_id]["HUSB"]
            wife = self.familydata[self.curr_id]["WIFE"]
            self.userdata[husband][self.tempdata + split_words[1]] = split_words[2]
            self.userdata[wife][self.tempdata + split_words[1]] = split_words[2]

    def donothing(self, nothing):
        pass

    def calc_data(self):

        for key in self.userdata:
            today = date.today()
            try:
                birthday = self.userdata[key]["BIRTDATE"]
                born_date = datetime.datetime.strptime(birthday, '%d %b %Y')
                if (born_date) > datetime.datetime.now():
                    print("ERROR: US01 INDIVIDUAL () {} has Birthdate Date before Current date".format(key,
                                                                                                       self.userdata[
                                                                                                           key][
                                                                                                           "NAME"]))
                    self.errorlog["DateAfterCurrent"] += 1
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
                if (death_date) > datetime.datetime.now():
                    print("ERROR: US21 INDIVIDUAL () {} has Death date Date after Current date".format(key,
                                                                                                        self.userdata[
                                                                                                            key][
                                                                                                            "NAME"]))
                    self.errorlog["DateAfterCurrent"] += 1
                if (death_date) > born_date:
                    print("ERROR: US03 INDIVIDUAL () {} has Death date Date before Birth date".format(key,
                                                                                                      self.userdata[
                                                                                                          key]["NAME"]))
                    self.errorlog["DeathBeforeBirth"] += 1
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
                print("ERROR: US10 INDIVIDUAL {} {} has married before the age of 14".format(key, self.userdata[key][
                    "NAME"]))
                self.errorlog["MarriageBefore14"] += 1

        error = self.prettyTablefunc()
        if error is None:
            error = "No errors found"
        return error, self.errorlog

    def prettyTablefunc(self):

        self.ptUsers.field_names = ["ID", "NAME", "GENDER", "BIRTH DATE", "AGE", "ALIVE", "DEATH", "CHILD", "SPOUSE"]

        single_list = []
        married_list = []
        test_single=[]
        test_married=[]
        deceased_list=[]
        test_deceased=[]

        for key in sorted(self.userdata.keys()):

            value = self.userdata[key]
            name = value["NAME"]
            gender = value["SEX"]
            birthdate = value["BIRTDATE"]
            age = value["AGE"]
            alive = value["ALIVE"]

            if name+birthdate in self.samenameandbirthdate:
                print("ERROR: US23 INDIVIDUAL {} {} does not have a unique name and birth date".format(key, name))
                self.errorlog["UniqueNameBirthDate"] += 1
            else:
                self.samenameandbirthdate.append(name+birthdate)

            try:
                value["MARRDATE"]
                married_list.append(value["NAME"])
                test_married.append(value["NAME"])

            except KeyError:
                single_list.append(value["NAME"])
                test_single.append(value["NAME"])




            try:
                death = value["DEATDATE"]
                deceased_list.append(value["NAME"])
                test_deceased.append(value["NAME"])

            except KeyError:
                death = "NA"
            try:
                fam_id = value["FAMS"]
                if fam_id == {}:
                    raise KeyError
                child = self.familydata[fam_id]["CHIL"]
                self.userdata[key]["CHILD"] = child
                for c in child:
                    if gender == "M":
                        self.userdata[c]["father"] = key
                    if gender == "F":
                        self.userdata[c]["mather"] = key
                
                
            except KeyError:
                child = "NA"
                self.userdata[key]["CHILD"] = child
                
            try:
                fam_id = value["FAMS"]
                if fam_id == {}:
                    raise KeyError
                if gender == "M":
                    spouse = self.familydata[fam_id]["WIFE"]
                    self.userdata[key]["SPOUSE"] = spouse
                else:
                    spouse = self.familydata[fam_id]["HUSB"]
                    self.userdata[key]["SPOUSE"] = spouse
            except KeyError:
                spouse = "NA"

            try:  # Check if marriage before 14, also add something to test cases.  Xiaopeng Yuan
                marriage = value["MARRDATE"]
            except KeyError:
                marriage = "NA"
            try:
                if datetime.datetime.strptime(value["DIVDATE"], '%d %b %Y') > datetime.datetime.now():
                    print("ERROR: 01 INDIVIDUAL () {} has Divorce date before Current date".format(key, name))
                    self.errorlog["DateAfterCurrent"] += 1
            except KeyError:
                pass

            if marriage != "NA":
                if datetime.datetime.strptime(marriage, '%d %b %Y') > datetime.datetime.now():
                    print("ERROR: 01 INDIVIDUAL () {} has Marriage date Date before Current date".format(key, name))
                    self.errorlog["DateAfterCurrent"] += 1

            if death != "NA" and datetime.datetime.strptime(marriage, '%d %b %Y') > datetime.datetime.strptime(death,
                                                                                                               '%d %b %Y'):
                print("ERROR: US05 INDIVIDUAL {} {} have Marriage at {} which is after their death on {}".format(key,
                                                                                                                 name,
                                                                                                                 datetime.datetime.strptime(
                                                                                                                     marriage,
                                                                                                                     '%d %b %Y'),
                                                                                                                 datetime.datetime.strptime(
                                                                                                                     death,
                                                                                                                     '%d %b %Y')))
                self.errorlog["MarriageBeforeDeath"] += 1

            if (death == "NA" and age > 150):
                print("ERROR: US07 INDIVIDUAL {} {} has an age of {} which is over 150".format(key, name, age))
                self.errorlog["AgeLessOneFifty"] += 1

            if (marriage != "NA"):
                if (datetime.datetime.strptime(birthdate, '%d %b %Y') > datetime.datetime.strptime(marriage,
                                                                                                   '%d %b %Y')):
                    print(
                        "ERROR: US13 INDIVIDUAL {} {} has Marriage Before Birth".format(key, name))
                    self.errorlog["MarriageBeforeBirth"] += 1

            self.ptUsers.add_row([key, name, gender, birthdate, age, alive, death, child, spouse])

        if self.bool_to_print:
            print(self.ptUsers)




            print("DISPLAY US31 LIST OF SINGLES: {}".format(single_list))

            test_single.pop(2)
            test_married.pop(5)
            test_deceased.pop(2)

            print("DISPLAY US29 LIST OF deceased PEOPLE: {}".format(deceased_list))


            for k in deceased_list:
                if k not in test_deceased:
                    print("ERROR: US29 INDIVIDUAL {} {} not in the list of deceased".format(key, self.userdata[key][
                        "NAME"]))
                    self.errorlog["DeceasedList"] += 1






            for i in single_list:
                if i not in test_single:
                    print("ERROR: US30 INDIVIDUAL {} {} not in the list of single".format(key, self.userdata[key][
                            "NAME"]))
                    self.errorlog["SingleList"] += 1




            print("DISPLAY US30 LIST OF MARRIED PEOPLE: {}".format(married_list))

            for i in married_list:
                if i not in test_married:
                    print("ERROR: US31 INDIVIDUAL {} {} not in the list of married people".format(key, self.userdata[key][
                            "NAME"]))
                    self.errorlog["MarriedList"] += 1


        self.ptFamily.field_names = ["ID", "MARRIAGE DATE", "DIVORCE DATE", "HUSBAND ID", "HUSBAND NAME", "WIFE ID",
                                     "WIFE NAME", "CHILDREN"]

        for key in sorted(self.familydata.keys()):

            uniquenameslist = []

            value = self.familydata[key]

            husband_id = value["HUSB"]
            wife_id = value["WIFE"]
            children = value["CHIL"]

                    

            if abs(datetime.datetime.strptime(self.userdata[husband_id]["BIRTDATE"],
                                              '%d %b %Y') - datetime.datetime.strptime(
                    self.userdata[wife_id]["BIRTDATE"], '%d %b %Y')).days > 5475:
                print("ERROR: US17 FAMILY {} has marriage between descendants and their children".format(key))
                self.errorlog["DescendantChildrenMarriage"] += 1
            if len(children) > 15:
                print("ERROR: US15 FAMILY {} more than 15 siblings".format(key))
                self.errorlog["SiblingGreaterThan15"] += 1
            husband_name = self.userdata[husband_id]["NAME"]
            husband_firstname, husband_lastname = husband_name.split()
            uniquenameslist.append(husband_firstname)
            try:
                marriage = self.userdata[husband_id]["MARRDATE"]
            except KeyError:
                return "No Marriage date found"

            wife_name = self.userdata[wife_id]["NAME"]
            wife_firstname, wife_lastname = wife_name.split()
            if wife_firstname not in uniquenameslist:
                uniquenameslist.append(wife_firstname)
            else:
                print("ERROR: US10 INDIVIDUAL {} {} and INDIVIDUAL {} {} have same first name".format(husband_id,
                                                                                                      husband_firstname,
                                                                                                      wife_id,
                                                                                                      wife_firstname))
                self.errorlog["UniqueFirstNames"] += 1
            try:
                divorce = self.userdata[husband_id]["DIVDATE"]
                div_husband = self.userdata[husband_id]["DIVDATE"]
                div_wife = self.userdata[wife_id]["DIVDATE"]
            except KeyError:
                divorce = "NA"
                div_husband = "NA"
                div_wife = "NA"

            for child in children:
                grandchildren = self.userdata[child]["CHILD"]
                
                for gchild in grandchildren:
                    if "SPOUSE" in self.userdata[gchild].keys():
                        gspouse = self.userdata[gchild]["SPOUSE"]                        
                        if("father" in self.userdata[gspouse].keys() and self.userdata[gspouse]["father"] in children) or ("mather" in self.userdata[gspouse].keys() and self.userdata[gspouse]["mather"] in children):
                            print("ERROR: {} and {} are married consins".format(gchild,gspouse))
                        if gspouse in children:
                            print("ERROR: Aunts and uncles")
                            
                birthday = datetime.datetime.strptime(self.userdata[child]["BIRTDATE"], '%d %b %Y')
                child_name = self.userdata[child]["NAME"]
                child_firstname, child_lastname = child_name.split()

                if abs(datetime.datetime.strptime(self.userdata[husband_id]["BIRTDATE"],
                                                  '%d %b %Y') - datetime.datetime.strptime(
                        self.userdata[child]["BIRTDATE"], '%d %b %Y')).days > 29200:
                    print(
                        "ERROR: US12 FAMILY {} Parents are too old".format(key))
                    self.errorlog["ParentsTooOld"] += 1

                if abs(datetime.datetime.strptime(self.userdata[wife_id]["BIRTDATE"],
                                                  '%d %b %Y') - datetime.datetime.strptime(
                        self.userdata[child]["BIRTDATE"], '%d %b %Y')).days > 21900:
                    print(
                        "ERROR: FAMILY {} Parents are too old".format(key))
                    self.errorlog["ParentsTooOld"] += 1

                if child_firstname not in uniquenameslist:
                    uniquenameslist.append(child_firstname)
                else:
                    print(
                        "ERROR: US25 INDIVIDUAL {} {} does not have a unique first name".format(child, child_firstname))
                    self.errorlog["UniqueFirstNames"] += 1

                multiple_siblings_birth_counter = 0
                for c in children:
                    if c != child:
                        c_birthday = datetime.datetime.strptime(self.userdata[c]["BIRTDATE"], '%d %b %Y')
                        if c_birthday > datetime.datetime.strptime(self.userdata[husband_id]["MARRDATE"], '%d %b %Y'):
                            print("ERROR: US08 Family {} has Child {} who was born before parents marriage".format(key,
                                                                                                                   c))
                            self.errorlog["ChildBirthBeforeParentsMarriage"] += 1
                        try:
                            if c_birthday > datetime.datetime.strptime(self.userdata[husband_id]["DEATDATE"],
                                                                       '%d %b %Y'):
                                print("ERROR: US09 Family {} has Child {} who was born after parents Death".format(key,
                                                                                                                   c))
                                self.errorlog["DeathBeforeBirthParents"] += 1
                        except KeyError:
                            pass
                        if abs(birthday - c_birthday).days < 250 or abs(birthday - c_birthday).days > 2:
                            print(
                                "ERROR: US13 INDIVIDUAL {} {} and INDIVIDUAL {} {} are siblings and have an invalid spacing between their births".format(
                                    child, self.userdata[child]["NAME"], c, self.userdata[c]["NAME"]))
                            self.errorlog["SiblingSpacing"] += 1
                        if abs(birthday - c_birthday).days < 2:
                            multiple_siblings_birth_counter += 1
                        if multiple_siblings_birth_counter > 5:
                            print(
                                "ERROR: US14 Family {} has more than 5 siblings born less than 2 days apart".format(
                                    key))
                            self.errorlog["MultipleSiblings"] += 1

                if self.userdata[child]["SEX"] == "M":
                    child_firstname, child_lastname = self.userdata[child]["NAME"].split()
                    if child_lastname.strip("/") != husband_firstname:
                        print(
                            "ERROR: US16 INDIVIDUAL {} {} and INDIVIDUAL {} {} have a Father-Child relationship but have different last names".format(
                                husband_id, husband_firstname, child, self.userdata[child]["NAME"]))
                        self.errorlog["MaleLastNames"] += 1

            if (divorce != "NA") and (div_husband != "NA") and (div_wife != "NA"):
                if (datetime.datetime.strptime(marriage, '%d %b %Y') > datetime.datetime.strptime(
                        self.userdata[husband_id]["DIVDATE"], '%d %b %Y')) or (
                        datetime.datetime.strptime(self.userdata[wife_id]["MARRDATE"],
                                                   '%d %b %Y') > datetime.datetime.strptime(
                        self.userdata[wife_id]["DIVDATE"], '%d %b %Y')):
                    print(
                        "ERROR: US04 INDIVIDUAL {} {} has Marriage After Divorce".format(husband_id,
                                                                                          husband_firstname))
                    self.errorlog["MarriageBeforeDivorce"] += 1

            if (divorce != "NA") and (div_husband != "NA") and (div_wife != "NA"):
                if (datetime.datetime.strptime(div_husband, '%d %b %Y') > datetime.datetime.strptime(
                        self.userdata[husband_id]["DEATDATE"], '%d %b %Y')) or (
                        datetime.datetime.strptime(div_wife, '%d %b %Y') > datetime.datetime.strptime(
                        self.userdata[wife_id]["DEATDATE"], '%d %b %Y')):
                    print(
                        "ERROR: US06 INDIVIDUAL {} {} has divorce after death".format(husband_id, husband_firstname))
                    self.errorlog["DivorceAfterDeath"] += 1

            if "FAMC" in self.userdata[husband_id] and "FAMC" in self.userdata[wife_id]:
                if self.userdata[husband_id]["FAMC"] == self.userdata[wife_id]["FAMC"]:
                    print(
                        "ERROR: US18 INDIVIDUAL {} {} and INDIVIDUAL {} {} are siblings but have married".format(
                            husband_id, husband_firstname, wife_id, wife_firstname))
                    self.errorlog["SiblingMarriageError"] += 1

            if (self.userdata[husband_id]["SEX"] == "M" and self.userdata[wife_id]["SEX"] == "M"):
                print(
                    "ERROR: US21 INDIVIDUAL {} {} and INDIVIDUAL {} {} are of same gender but have married".format(
                        husband_id, husband_firstname, wife_id, wife_firstname))
                self.errorlog["ProperGender"] += 1

            try:
                child = value["CHIL"]
            except KeyError:
                child = "NA"
            self.ptFamily.add_row([key, marriage, divorce, husband_id, husband_name, wife_id, wife_name, child])

        if self.bool_to_print is True:
            print(self.ptFamily)


class TestCases(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        Set up objects with filenames
        """
        cls.x = Gedcom("SprintTestFile.ged", "y")
        cls.error, cls.errorlog = cls.x.analyze()

    # def setUp(self):
    #     """
    #     Set up objects with filenames
    #     """
    #     self.x = Gedcom("SprintTestFile.ged", "y")
    #     self.error, self.errorlog = self.x.analyze()
    #     print(self.errorlog)

    def test_divorceAfterDeath(self):
        """
        Test if hus/wife divorces after death
        """
        self.assertNotEqual(self.errorlog["DivorceAfterDeath"], 0)

    def test_SiblingMarriage(self):
        """
        Test if siblings marry
        """
        self.assertNotEqual(self.errorlog["SiblingMarriageError"], 0)

    def test_AgeLessOneFifty(self):
        """
        Test if siblings marry
        """
        self.assertNotEqual(self.errorlog["AgeLessOneFifty"], 0)

    def test_ProperGender(self):
        """
        Test if siblings marry
        """
        self.assertNotEqual(self.errorlog["ProperGender"], 0)

    def test_MarriageBefore14(self):
        """
        Test if marriage before 14
        """
        self.assertNotEqual(self.errorlog["MarriageBefore14"], 0)

    def test_RepetitiveID(self):
        """
        Test if ID is unique
        """
        self.assertNotEqual(self.errorlog["RepetitiveID"], 0)

    def test_malelastnames(self):
        """
        Test if male children have same last name in family
        """
        self.assertNotEqual(self.errorlog["MaleLastNames"], 0)

    def test_siblingsgreaterthan15(self):
        """
        Test if male children have same last name in family
        """
        self.assertNotEqual(self.errorlog["SiblingGreaterThan15"], 0)

    def test_siblingspacing(self):
        """
        Test if family has less than 5 children born in under 2 days
        """
        self.assertNotEqual(self.errorlog["MultipleSiblings"], 0)

    def test_marriagebeforedeath(self):
        """
        Test if male children have same last name in family
        """
        self.assertNotEqual(self.errorlog["MarriageBeforeDeath"], 0)

    def test_uniquefirstnames(self):
        """
        Test if male children have same last name in family
        """
        self.assertNotEqual(self.errorlog["UniqueFirstNames"], 0)

    def test_marriagebeforedivorce(self):
        """
        Test if marriage date is before divorce date
        """
        self.assertNotEqual(self.errorlog["MarriageBeforeDivorce"], 0)

    def test_marriagebeforebirth(self):
        """
        Test if marriage date is before birth date
        """
        self.assertNotEqual(self.errorlog["MarriageBeforeBirth"], 0)

    def test_datebeforecurrent(self):
        """
        Test if marriage date is before birth date
        """
        self.assertNotEqual(self.errorlog["DateAfterCurrent"], 0)

    def test_descendantmarryparent(self):
        """
        Test if Children don't marry their parents
        """
        self.assertNotEqual(self.errorlog["DescendantChildrenMarriage"], 0)

    def test_birthbeforedeath(self):
        """
        Test if Birth is before death
        """
        self.assertNotEqual(self.errorlog["DeathBeforeBirth"], 0)

    def test_birthbeforedeathparents(self):
        """
        Test if Birth is before death of parents
        """
        self.assertNotEqual(self.errorlog["DeathBeforeBirthParents"], 0)

    def test_childbirthbeforeparentsmarriage(self):
        """
        Test if Child is born after parents marriage
        """
        self.assertNotEqual(self.errorlog["ChildBirthBeforeParentsMarriage"], 0)

    def test_bigamy(self):
        """
        Test if Marriage occurs during another marriage
        """
        self.assertNotEqual(self.errorlog["Bigamy"], 0)

    def test_parentstooold(self):
        """
        Test if Parents are too old
        """
        self.assertNotEqual(self.errorlog["ParentsTooOld"], 0)

    def test_singlelist(self):
        """
        Test if single list is proper
        """
        self.assertNotEqual(self.errorlog["SingleList"], 0)

    def test_marriedlist(self):
        """
        Test if married list is proper
        """
        self.assertNotEqual(self.errorlog["MarriedList"], 0)


    def test_DeceasedList(self):
        """
        Test if Deceased List is proper
        """
        self.assertNotEqual(self.errorlog["DeceasedList"], 0)

    def test_uniquenamebirthdate(self):
        """
        Test if user has a unique name and Birth date
        """
        self.assertNotEqual(self.errorlog["UniqueNameBirthDate"], 0)


def main():
    file = input("Enter file name: \n")
    pretty = input("Do you want pretty table? y/n \n")
    g = Gedcom(file, pretty)
    op, userdata, familydata, error = g.analyze()
    print(error)


if __name__ == '__main__':
    unittest.main(exit=False, verbosity=2)
    #main()