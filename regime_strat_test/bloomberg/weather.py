import pandas as pd
from datetime import datetime, timedelta

from jain_commods.core.interfaces.bloomberg import bsrch_handler, BBGQuery

from jain_commods.fundamental.weather import utils


def _prepare_bbg_data(data_type, df):
    
    if data_type.lower()=='actual-weather':
        df = df.set_index('Location Time')
        df.index = pd.to_datetime(df.index,utc=True).tz_localize(None)
        df.index = df.index.floor('D')
        
        df = df.drop(columns=['Reported Time'])
        
    elif data_type.lower() in  ['forecast-weather','normal-weather']:
        # Strip time zone info (to avoid worrying about DST etc)
        df['Location Time'] = df['Location Time'].str[:-6]
        df['Location Time'] = pd.to_datetime(df['Location Time'])
        df = df.set_index('Location Time')
        df = df.drop(columns=['Reported Time'])
        
    elif data_type.lower()=='forecast-energy':
        
        df['Reported Time (UTC)'] = df['Reported Time (UTC)'].str[:-6]
        df['Reported Time (UTC)'] = pd.to_datetime(df['Reported Time (UTC)'])
        df = df.set_index('Reported Time (UTC)')
        
    # TODO: we might need to re-instate this?
    # df = df.replace('', np.nan).astype(float)
        
    return df
    


def get_bbg_data(data_type, location, standard_col_names=True, **kwargs):
    
    # Define common config (NB: this is heavily reduced due to adding EFOR forecasts in here)
    override_configs = [
        ('location', location),
    ]
    
    today = pd.to_datetime(datetime.now()).normalize()
    
    fields_forecast_default = 'TEMPERATURE|WIND_SPEED|CLOUD_COVER|FEELS_LIKE_TEMPERATURE|HDD_65F|CDD_65F|HDD_18C|CDD_18C|PRECIPITATION'
    fields_normals_ec46 = 'TEMPERATURE|WIND_SPEED|PRECIPITATION' #'|CLOUD_COVER'
    
    # Construct config based on what data we want
    if data_type.lower()=='actual-weather':
        
        # Set domain 
        request_domain = 'COMDTY:WEATHER'

        # Get args
        start_date = kwargs.get('start_date', datetime(2021,1,1))
        end_date = kwargs.get('end_date', datetime.today()-timedelta(days=1))
        fields = kwargs.get('fields', fields_forecast_default.replace('PRECIPITATION', 'PRECIPITATION_24HR'))
        
        # Add to the config
        override_configs.append(('provider','wsi')) # hard coded
        override_configs.append(('model','ACTUALS')) # hard coded
        override_configs.append(('frequency','DAILY')) # hard coded
        override_configs.append(('location_time','TRUE')) # hard coded
        override_configs.append(('target_start_date', start_date.strftime('%Y-%m-%d')))
        override_configs.append(('target_end_date', end_date.strftime('%Y-%m-%d')))
        override_configs.append(('fields', fields)) 

    
    elif data_type.lower()=='forecast-weather':
        
        # Set domain 
        request_domain = 'COMDTY:WEATHER'
        
        # Get args
        model = kwargs.get('model', 'ECMWF')
        model_type = kwargs.get('model_type','ENSEMBLE_MEAN')
        pub_date = kwargs.get('pub_date', today if model_type=='ENSEMBLE_MEAN' else today - timedelta(days=1))
        fields  = kwargs.get('fields', fields_normals_ec46 if model_type=='MONTH_AHEAD' else fields_forecast_default)
        
        # Add to the config
        override_configs.append(('provider','wsi')) # hard coded
        override_configs.append(('frequency','DAILY')) # hard coded
        override_configs.append(('location_time','TRUE')) # hard coded
        override_configs.append(('model', model))
        override_configs.append(('type', model_type))
        override_configs.append(('publication_date', pub_date.strftime('%Y-%m-%dT%H:00:00')))
        override_configs.append(('fields', fields)) 
        
    elif data_type.lower()=='normal-weather':
        
        # Set domain 
        request_domain = 'COMDTY:WEATHER'
        
        # Get args
        model = kwargs.get('model', '10_year_normal') # 30_year_normal / 5_year_normal
        fields  = kwargs.get('fields', fields_normals_ec46)
        start_date = kwargs.get('start_date', datetime.today()-timedelta(days=365))
        end_date = kwargs.get('end_date', datetime.today()+timedelta(days=365))
        
        # Add to the config
        override_configs.append(('provider','wsi')) # hard coded
        override_configs.append(('frequency','DAILY')) # hard coded
        override_configs.append(('location_time','TRUE')) # hard coded
        override_configs.append(('model',model))
        override_configs.append(('target_start_date', start_date.strftime('%Y-%m-%d')))
        override_configs.append(('target_end_date', end_date.strftime('%Y-%m-%d')))
        override_configs.append(('fields', fields)) 
    
    elif data_type.lower()=='forecast-energy':
        
        # Set domain 
        request_domain = 'COMDTY:MODEL'
        
        # Get args
        model = kwargs.get('model', 'Gas_Consumption_ResCom') # Solar_Generation / Wind_Generation / Gross_Power_Demand
        weather_model = kwargs.get('weather_model', 'ECMWF')
        weather_model_subtype = kwargs.get('weather_model_subtype', 'Ensemble') # Deterministic
        ensemble_type = kwargs.get('ensemble_type', 'Mean') # Max, Min
        pub_date = kwargs.get('pub_date', today)
        
        # Add to the config
        override_configs.append(('provider','Bloomberg')) # hard coded
        override_configs.append(('model', model)) 
        override_configs.append(('weather_model',weather_model))
        override_configs.append(('subtype',weather_model_subtype))
        # We only apply this for Ensemble models
        if weather_model_subtype=='Ensemble':
            override_configs.append(('ensemble_type', ensemble_type))
        override_configs.append(('weather_publication_date', pub_date.strftime('%Y-%m-%dT%H:00:00')))    
    
    else:
        raise Exception(f'Unknown data_type {data_type}')
    
    # print(override_configs)
    bbg_session = BBGQuery(p_on_server=True)._start_session_server()
    
    bbg_session.openService('//blp/exrsvc')
    exrService = bbg_session.getService('//blp/exrsvc')
    request = exrService.createRequest('ExcelGetGridRequest')
    # Set property as per above
    request.set('Domain', request_domain)
    overrides = request.getElement("Overrides")
      
    # Apply config defined above
    overrides = request.getElement("Overrides")
    for name, value in override_configs:
        override = overrides.appendElement()
        override.setElement("name", name)
        override.setElement("value", value)        

    # Query bloombberg
    bbg_session.sendRequest(request)
    
    # Loop through the results and put them into a DataFrame
    output = []
    try:
        while (True):
            event = bbg_session.nextEvent(500)
            if event.eventType() != bsrch_handler.BLP_RESPONSE and \
                    event.eventType() != bsrch_handler.BLP_PARTIAL_RESPONSE:
                continue
            for msg in event:
                df = bsrch_handler.getBSRCHData(msg)
                if len(df) > 0:
                    df_clean = _prepare_bbg_data(data_type, df)
                    output.append(df_clean)
            if event.eventType() == bsrch_handler.BLP_RESPONSE:
                break
    except Exception as e:
        print(f"An error occurred: {e}")
        
    # Create output dataframe
    if len(output)>=1:
        df_output = pd.concat(output, axis=1)
        
        # Rename to our standard column names
        if standard_col_names:
            return df_output.rename(columns=utils.bbg_cols)
        else:
            return df_output
        
    else:
        # raise Exception('No data found')
        # TODO: what should we do here? Is there a better way to check if a forecast has been published yet?
        print('No data found')
        return pd.DataFrame()




if __name__ == "__main__":
    # Example usage
    

    # Weather actuals (note: 5year limit on querying history)
    actuals = get_bbg_data('actual-weather','BE', start_date=datetime(2019,1,1), end_date=datetime(2021,1,1))
    
    # Weather forecasts
    fcast_ecens = get_bbg_data('forecast-weather','BE')
    fcast_ec46 = get_bbg_data('forecast-weather','BE', model_type='MONTH_AHEAD')
    fcast_gfsens = get_bbg_data('forecast-weather','BE', model='GFS')
    
    # Seasonal normals
    seasonal_normals = get_bbg_data('normal-weather','BE')
    
    # Energy forecasts
    fcast_ldz_ecens = get_bbg_data('forecast-energy', 'BE') # NB: LDZ is default model
