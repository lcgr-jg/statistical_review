
"""

BPIPE code to pull bbg data

Sample provided by Manish (already being used by Ben as of Nov-24)

"""

import datetime as dt
from datetime import timedelta, datetime
import atexit

import blpapi
import numpy as np
import pandas as pd
from pandas import DataFrame


current_date = datetime.today()#.strftime('%Y-%m-%d')
EXCEPTIONS = blpapi.Name("exceptions")
FIELD_ID = blpapi.Name("fieldId")
REASON = blpapi.Name("reason")
CATEGORY = blpapi.Name("category")
DESCRIPTION = blpapi.Name("description")

SessionConnectionDown = blpapi.Name("SessionConnectionDown")
SessionConnectionUp = blpapi.Name("SessionConnectionUp")
SessionTerminated = blpapi.Name("SessionTerminated")
ServiceDown = blpapi.Name("ServiceDown")
SlowConsumerWarning = blpapi.Name("SlowConsumerWarning")
SlowConsumerWarningCleared = blpapi.Name("SlowConsumerWarningCleared")
DataLoss = blpapi.Name("DataLoss")

ServiceName = blpapi.Name("serviceName")
# authorization
AUTHORIZATION_SUCCESS = blpapi.Name("AuthorizationSuccess")
AUTHORIZATION_FAILURE = blpapi.Name("AuthorizationFailure")
AUTHORIZATION_REVOKED = blpapi.Name("AuthorizationRevoked")
TOKEN_SUCCESS = blpapi.Name("TokenGenerationSuccess")
TOKEN_FAILURE = blpapi.Name("TokenGenerationFailure")
TOKEN = blpapi.Name("token")

g_session = None
g_sessionStarted = False
g_subscriptions = None
g_identity = None
g_authCorrelationId = None


class BBGQuery:
    # use a Singleton to manage the session and query while running dashboard scripts
    _instance = None

    def __new__(cls, p_on_server=False):
        if cls._instance is None:
            cls._instance = super(BBGQuery, cls).__new__(cls)
            cls._instance.session = (cls._instance._start_session_server() if p_on_server
                                     else cls._instance._start_session())
            cls._instance.on_server = p_on_server
            atexit.register(cls._instance._close_session)
        return cls._instance

    def _start_session(self):
        session = blpapi.Session()
        if not session.start():
            raise Exception("Failed to start Bloomberg session.")
        if not session.openService("//blp/refdata"):
            raise Exception("Failed to open Bloomberg refdata service.")
        # print("Bloomberg session created.")
        return session

    def _start_session_server(self):
        options = blpapi.SessionOptions()
        # Note: SessionOptions.SessionName require SDK version 3.23.x or later
        options.sessionName = 'Example Session'

        # Server address setup
        # Prod: Tech1ProdBPipe47537.jainglobal.net OR Tech1ProdBPipe47538.jainglobal.net
        # Non-prod: tech1devbpipe49407.jainglobal.net OR or tech1devbpipe49408.jainglobal.net
        options.setServerAddress("Tech1ProdBPipe47537.jainglobal.net", 8194, 0)

        
        authOptions = blpapi.AuthOptions.createWithApp("JAIN:commoditiespmdashboard")
        g_authCorrelationId = blpapi.CorrelationId("authCorrelation")
        options.setSessionIdentityOptions(authOptions, g_authCorrelationId)
        # print("Session options: %s" % options)
        # eventHandler = SubscriptionEventHandler()

        # Create a Session
        # session = blpapi.Session(options, eventHandler.processEvent)
        session = blpapi.Session(options)

        # Start a Session
        if not session.start():
            raise Exception("Failed to start session.")

        service = "//blp/refdata"
        if not session.openService(service):
            # print ("Failed to open %s service" % service)
            return
        return session

    def _close_session(self):
        if self.session:
            self.session.stop()
            # print("Bloomberg session closed.")

    def _get_different_type(self, p_datatype, p_field, p_fieldData):
        if p_datatype == blpapi.DataType.STRING:
            ret = p_fieldData.getElementAsString(p_field)
        elif p_datatype == blpapi.DataType.FLOAT64:
            ret = p_fieldData.getElementAsFloat(p_field)
        elif p_datatype == blpapi.DataType.INT32:
            ret = p_fieldData.getElementAsInteger(p_field)
        elif p_datatype == blpapi.DataType.DATE:
            ret = p_fieldData.getElementAsDatetime(p_field)
        elif p_datatype == blpapi.DataType.DATETIME:
            ret = p_fieldData.getElementAsDatetime(p_field)
        else:
            ret = np.nan
        return ret

    def fetch_live(self,
                   tickers,
                   fields,
                   p_overrides: dict = None,
                   p_pd_datetime: bool = False) -> pd.DataFrame | None:
        """
        Fetch live prices, similar to BDP

        :param tickers:
        :param fields:
        :param p_overrides: overrides for the request
        :param p_pd_datetime: convert index to pandas datetime
        :return:
        """
        refDataService = self.session.getService("//blp/refdata")
        request = refDataService.createRequest("ReferenceDataRequest")

        if isinstance(tickers, str):
            tickers = [tickers]
        if isinstance(fields, str):
            fields = [fields]

        for ticker in tickers:
            request.getElement("securities").appendValue(ticker)
        for field in fields:
            request.getElement("fields").appendValue(field)
        if p_overrides:
            overrides = request.getElement("overrides")
            override1 = overrides.appendElement()
            for k, v in p_overrides.items():
                override1.setElement(k, v)

        self.session.sendRequest(request)
        data = {}
        while True:
            event = self.session.nextEvent(500)
            for msg in event:
                if msg.hasElement("securityData"):
                    securityDataArray = msg.getElement("securityData").values()
                    for securityData in securityDataArray:
                        ticker = securityData.getElementAsString("security")
                        fieldData = securityData.getElement("fieldData")
                        data[ticker] = dict()
                        for field in fields:
                            try:
                                if fieldData.hasElement(field):
                                    datatype = fieldData.getElement(field).datatype()
                                    data[ticker][field] = self._get_different_type(datatype, field, fieldData)
                            except:
                                data[ticker][field] = np.nan
                                continue
            if event.eventType() == blpapi.Event.RESPONSE:
                break
        data = pd.DataFrame.from_dict(data, orient='index')
        if p_pd_datetime:
            data.index = pd.to_datetime(data.index)
        return data

    def fetch_hist(self,
                   p_ticker,
                   p_field,
                   p_start: dt.datetime = None,
                   p_end: dt.datetime = None,
                   p_opt_args: dict = None,
                   p_spec_time: bool = None,
                   p_sec_interval: int = None,
                   p_pd_datetime: bool = False) -> DataFrame | None:
        """
        Fetch hist prices, similar to BDH

        :param p_ticker: str or list of tickers
        :param p_field: str or list of fields
        :param p_start: start date
        :param p_end: end date
        :param p_opt_args: other optional arguments. Similar to BDH()'s arguments after end date
        :param p_spec_time: specific time for pulling
        :param p_sec_interval: if p_spec_time, the time window in seconds
        :param p_pd_datetime: convert index to pandas datetime
        :return: DataFrame with requested data
        """
        if p_spec_time:
            # it diverts to IntradayBarRequest
            return self.__fetch_hist_spec_time(p_ticker, p_field, p_start, p_end, p_sec_interval)
        else:
            # use HistoricalDataRequest
            ref_data_service = self.session.getService("//blp/refdata")
            request = ref_data_service.createRequest("HistoricalDataRequest")
            if isinstance(p_ticker, str):
                p_ticker = [p_ticker]
            if isinstance(p_field, str):
                p_field = [p_field]
            for this_ticker in p_ticker:
                request.getElement("securities").appendValue(this_ticker)
            for this_field in p_field:
                request.getElement("fields").appendValue(this_field)
            request.set("startDate", p_start.strftime('%Y%m%d'))
            request.set("endDate", p_end.strftime('%Y%m%d'))
            if p_opt_args is not None:
                for k, v in p_opt_args.items():
                    request.set(k, v)
            request.set("periodicitySelection", "DAILY")

            self.session.sendRequest(request)

            data = dict()
            while True:
                event = self.session.nextEvent()
                for msg in event:
                    if msg.hasElement("securityData"):
                        security_data = msg.getElement("securityData")
                        ticker = security_data.getElementAsString("security")
                        field_data = security_data.getElement("fieldData")
                        if ticker not in data:
                            data[ticker] = []
                        for fields in field_data.values():
                            date = fields.getElementAsDatetime("date")
                            row = {'date': date}
                            for this_field in p_field:
                                if fields.hasElement(this_field):
                                    datatype = fields.getElement(this_field).datatype()
                                    row[this_field] = self._get_different_type(datatype, this_field, fields)
                                    # row[this_field] = fields.getElementAsFloat(this_field)
                                else:
                                    row[this_field] = np.nan
                            data[ticker].append(row)
                if event.eventType() == blpapi.Event.RESPONSE:
                    break

            # Convert dictionary to DataFrame and join vertically
            all_data = []
            for ticker, rows in data.items():
                df = pd.DataFrame(rows)
                if df.empty:
                    continue
                df.set_index('date', inplace=True)
                df.columns = [f"{ticker}_{col}" for col in df.columns]
                all_data.append(df)

            if all_data:
                ret = all_data[0]
                for df in all_data[1:]:
                    ret = ret.merge(df, how='outer', left_index=True, right_index=True)
            else:
                ret = pd.DataFrame()
            if p_pd_datetime:
                ret.index = pd.to_datetime(ret.index)
            return ret


    def __fetch_hist_spec_time(self,
                               p_ticker,
                               p_field,
                               p_start,
                               p_end,
                               p_sec_interval: int = None,
                               p_pd_datetime: bool = False) -> DataFrame | None:
        ref_data_service = self.session.getService("//blp/refdata")
        current_date = p_start
        ret = dict()
        sec_interval = 1 if not p_sec_interval else p_sec_interval
        while current_date <= p_end:
            request = ref_data_service.createRequest("IntradayBarRequest")
            request.set("security", p_ticker)
            request.set("eventType", p_field)
            request.set("startDateTime", current_date.strftime("%Y-%m-%dT%H:%M:%S"))
            request.set("endDateTime", (current_date+timedelta(seconds=sec_interval)).strftime("%Y-%m-%dT%H:%M:%S"))
            request.set("interval", sec_interval)

            # print("Sending Request:", request)
            self.session.sendRequest(request)

            # Process response
            while True:
                event = self.session.nextEvent(500)
                for msg in event:
                    if msg.hasElement("barData"):
                        value=np.nan
                        data = msg.getElement("barData").getElement("barTickData").values()
                        for bar in data:
                            value = bar.getElementAsFloat("open")
                        ret[current_date] = value
                if event.eventType() == blpapi.Event.RESPONSE:
                    break
            current_date += timedelta(days=1)
        df = pd.DataFrame.from_dict(ret, orient='index', columns=['value'])
        if p_pd_datetime:
            df.index = pd.to_datetime(df.index)
        return df


def generic_query(ticker):
    test_session = BBGQuery(p_on_server=True)
    ret = test_session.fetch_hist(ticker,
                                  "PX_LAST",
                                  dt.datetime(2018, 1, 1),
                                  dt.datetime(2024, 11,1))
    return ret


if __name__ == '__main__':
    print(generic_query("CNGDGDP Index"))
    print("Done.")