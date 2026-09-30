"""
Created on Tue Apr 16 08:27:38 2019

@author: Michael

Simple function to retrieve all values from an input blpapi element.

"""
import sys
import blpapi
import pandas as pd

# 8 Possible GetElement datatypes are:
# IntValue, LongValue, StringValue,
# FloatValue, DoubleValue, DateValue,
# TimeValue, DateTimeValue

INT_FIELD = blpapi.Name('IntValue')
LONG_FIELD = blpapi.Name('LongValue')
STRING_FIELD = blpapi.Name('StringValue')
FLOAT_FIELD = blpapi.Name('FloatValue')
DOUBLE_FIELD = blpapi.Name('DoubleValue')
DATE_FIELD = blpapi.Name('DateValue')
TIME_FIELD = blpapi.Name('TimeValue')
DATETIME_FIELD = blpapi.Name('DateTimeValue')
COLUMN_TITLES = blpapi.Name("ColumnTitles")
DATA_RECORDS = blpapi.Name("DataRecords")
NUM_RECORDS = blpapi.Name("NumOfRecords")
NUM_FIELDS = blpapi.Name("NumOfFields")
SECURITY_DATA = blpapi.Name("securityData")
FIELD_DATA = blpapi.Name("fieldData")


BLP_RESPONSE = blpapi.Event.RESPONSE
BLP_PARTIAL_RESPONSE = blpapi.Event.PARTIAL_RESPONSE


def getBSRCHColumnTitles(input_msg):
    # takes as input a returned message and parses the
    # column headers from the msg into a list
    header_list = []
    for this_title in input_msg.getElement(COLUMN_TITLES).values():
        header_list.append(this_title)
    return header_list


def createBSRCHDataFrame(input_msg):
    # function takes a BSRCH RESPONSE msg as input and outputs a matching dataframe object
    header_list = getBSRCHColumnTitles(input_msg)
    df = pd.DataFrame(data=None, index=None, columns=header_list)
    return df


def getBSRCHData(input_msg, output_df=0):
    # takes as input a returned message and parses out all
    # the data for the message. Returns the data as a pandas dataframe
    # Optional argument of output_df can be supplied allowing appending
    # to a previously retrieved dataset
    if output_df == 0:
        # no df was supplied so create it
        output_df = createBSRCHDataFrame(input_msg)
    else:
        numFields = input_msg.getElement(NUM_FIELDS).getValue()
        if numFields != output_df.Columns.Count():
            # the output dataframe does not match the input data - raise an error
            sys.exit("Supplied dataframe does not have same number of columns as BSRCH message")

    # otherwise we're good to go
    # loop through each record in data records values
    for this_record in input_msg.getElement(DATA_RECORDS).values():
        # this_record is a single record instance
        # these_fields = this_record.getElement("fieldData")
        # for this_field in these_fields:
        for elit in this_record.elements():
            int_list = getBSRCHFieldsAsList(elit)
            if len(int_list) > 0:
                output_df.loc[len(output_df)] = int_list
    return output_df


def getBSRCHFieldsAsList(input_element):
    # takes as input a single element row and returns the values as a list
    # create blank output list
    output_list = []

    for this_value in input_element.values():
        if this_value.hasElement(INT_FIELD):
            output_list.append(this_value.getElementAsInteger(INT_FIELD))
        elif this_value.hasElement(LONG_FIELD):
            output_list.append(this_value.getElementAsFloat(LONG_FIELD))
        elif this_value.hasElement(STRING_FIELD):
            output_list.append(this_value.getElementAsString(STRING_FIELD))
        elif this_value.hasElement(FLOAT_FIELD):
            output_list.append(this_value.getElementAsFloat(FLOAT_FIELD))
        elif this_value.hasElement(DOUBLE_FIELD):
            output_list.append(this_value.getElementAsFloat(DOUBLE_FIELD))
        elif this_value.hasElement(DATE_FIELD):
            output_list.append(this_value.getElementAsDatetime(DATE_FIELD))
        elif this_value.hasElement(TIME_FIELD):
            output_list.append(this_value.getElementAsDatetime(TIME_FIELD))
        elif this_value.hasElement(DATETIME_FIELD):
            output_list.append(this_value.getElementAsString(DATETIME_FIELD))
        else:
            # error - we've missed a value
            output_list.append('# Error: Unknown DataType in BSRCH Results')
    return output_list