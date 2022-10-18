import sys
import datetime
import itertools
import numpy as np
import pandas as pd 
import geopandas as gpd
from shapely.wkt import loads
from shapely.geometry import Point

### shortest path
sys.path.insert(0, '/Users/bingyu')
from sp import interface

### plotting
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib import rc
rc('font',**{'family':'serif','serif':['Times']})

### crs
project_crs='epsg:4326'

class Trains():
    def __init__(self):
        self.schedule_df = None
    
    def add_schedule(self, schedule_table):
        ### convert the cleaned GTFS data (schedule_table) into class attribute (self.schedule)
        schedule_list = []
        for row in schedule_table.itertuples():
            schedule_list.append((getattr(row, 'trip_id'),
                                  getattr(row, 'arrival_time'), getattr(row, 'departure_time'), 'stop', 
                                  getattr(row, 'route_stop_id'), getattr(row, 'shape_dist_traveled')))
            schedule_list.append((getattr(row, 'trip_id'),
                                  getattr(row, 'departure_time'), getattr(row, 'next_arrival_time'), 'on_link',
                                  '{}:{}'.format(getattr(row, 'route_stop_id'), 
                                                 getattr(row, 'next_route_stop_id')), 0))
        ### add final destination of the trip
        for row in schedule_table.groupby('trip_id').tail(1).itertuples():
            schedule_list.append((getattr(row, 'trip_id'),
                                  getattr(row, 'next_arrival_time'), getattr(row, 'next_arrival_time')+30, 'stop', 
                                  getattr(row, 'next_route_stop_id'), getattr(row, 'next_shape_dist_traveled')))
        self.schedule_df = pd.DataFrame(schedule_list, columns=['trip_id', 'time', 'next_time', 'status', 'location', 'shape_dist_traveled'])
        self.schedule_df = self.schedule_df.sort_values(by=['trip_id', 'time'], ascending=True)
    
    def add_network(self, schedule_table):
        
        ### process network
        all_links = schedule_table.drop_duplicates(subset=['route_stop_id', 'next_route_stop_id'])
        all_links = all_links[['route_stop_id', 'next_route_stop_id', 
                               'stop_lon', 'stop_lat', 'next_stop_lon', 'next_stop_lat']].copy()

        ### create nodes
        all_nodes = pd.DataFrame(np.vstack(
            [all_links[['route_stop_id', 'stop_lon', 'stop_lat']].values,
             all_links[['next_route_stop_id', 'next_stop_lon', 'next_stop_lat']].values]),
            columns=['route_stop_id', 'stop_lon', 'stop_lat'])
        all_nodes = all_nodes.drop_duplicates(subset=['route_stop_id'])
        all_nodes['stop_id'] = all_nodes['route_stop_id'].apply(lambda x: x.split('-')[1])
        all_nodes['type'] = 'platform'
        ### station nodes
        virtual_nodes = all_nodes.groupby('stop_id').agg({'stop_lon': np.mean, 'stop_lat': np.mean}).reset_index(drop=False)
        virtual_nodes['stop_lon'] *= 0.999999
        virtual_nodes['route_stop_id'] = virtual_nodes['stop_id'].apply(lambda x: 'all-{}'.format(x))
        virtual_nodes['type'] = 'station'
        all_nodes = pd.concat([all_nodes, virtual_nodes[all_nodes.columns]])
        all_nodes['node_id'] = np.arange(all_nodes.shape[0])
        all_nodes = gpd.GeoDataFrame(
            all_nodes, crs=project_crs, 
            geometry=[Point(xy) for xy in zip(all_nodes.stop_lon, all_nodes.stop_lat)])
        station_nm_id_dict = {getattr(row, 'route_stop_id'): getattr(
            row, 'node_id') for row in all_nodes.itertuples()}
        station_id_nm_dict = {getattr(row, 'node_id'): getattr(
            row, 'route_stop_id') for row in all_nodes.itertuples()}

        ### add transfer links
        transfer_links = []
        for stop_id, grp in all_nodes.groupby('stop_id'):
            for (stop1, stop2) in list(itertools.permutations(grp.to_dict('records'), 2)):
                transfer_links.append([stop1['route_stop_id'], stop2['route_stop_id'], 
                                       stop1['stop_lon'], stop1['stop_lat'], stop2['stop_lon'], stop2['stop_lat']])
        transfer_links_df = pd.DataFrame(transfer_links, columns=['route_stop_id', 'next_route_stop_id',
                                                                 'stop_lon', 'stop_lat', 'next_stop_lon', 'next_stop_lat'])
        all_links = pd.concat([all_links, transfer_links_df])

        ### map stop names to node_ids
        self.schedule_df['location_id'] = self.schedule_df['location'].map(station_nm_id_dict).fillna(-1)
        all_links['start_nid'] = all_links['route_stop_id'].map(station_nm_id_dict)
        all_links['end_nid'] = all_links['next_route_stop_id'].map(station_nm_id_dict)
        all_links['initial_weight'] = 1.0
        all_links['geometry'] = all_links.apply(
            lambda x: 'LINESTRING({} {}, {} {})'.format(
                x['stop_lon'], x['stop_lat'], x['next_stop_lon'], x['next_stop_lat']
            ), axis=1)
        all_links = all_links[['route_stop_id', 'next_route_stop_id', 'start_nid', 'end_nid',
                               'initial_weight', 'geometry']]
        all_links = gpd.GeoDataFrame(all_links, crs=project_crs, geometry=all_links['geometry'].map(loads))
        return all_nodes, all_links
    
    def generate_trajectory_plot(self, start_time, end_time, all_nodes, direction_id):
        ### get trace plot y axis
        all_nodes = all_nodes.sort_values(by='stop_lon', ascending=False)

        all_nodes['x'] = all_nodes['geometry'].x
        all_nodes['y'] = all_nodes['geometry'].y
        one_trip = self.schedule_df[(self.schedule_df['trip_id']=='10553.T9.21-U1-j22-1.4.H') & 
                                    (self.schedule_df['status']=='stop')]
        all_nodes = all_nodes.merge(one_trip[['location', 'shape_dist_traveled']], how='inner', 
                                                left_on='route_stop_id', right_on='location')
        all_nodes['distance'] = all_nodes['shape_dist_traveled']

        fig, ax = plt.subplots(figsize=(12, 4))
        stations = all_nodes[all_nodes['type']=='platform'].copy()
        ax.set_yticks(stations['distance'])
        ax.set_yticklabels(['{} ({})'.format(stop_id, distance) 
                            for (stop_id, distance) in zip(stations['stop_id'], stations['distance'])])
        ax.set_ylabel('Position', fontsize=15)
        x_ticks = np.arange(start_time, end_time, 600)
        x_ticklabels = [str(datetime.timedelta(seconds=int(t))) for t in x_ticks]
        ax.set_xticks(x_ticks)
        ax.set_xticklabels(x_ticklabels)
        ax.set_xlabel('Time', fontsize=15)

        ### get trace plot of the vehicles
        schedule = self.schedule_df.copy()
        schedule = schedule[(schedule['time']>=start_time) & (schedule['time']<=end_time)]

        i=0
        for trip_id, grp in schedule.groupby('trip_id'):
            schedule_plot_list = []
            if grp.iloc[0]['location'].split('-')[0] != direction_id: continue
            for row in grp[grp['status']=='stop'].itertuples():
                schedule_plot_list.append([getattr(row, 'time'), getattr(row, 'location').split('-')[1]])
                schedule_plot_list.append([getattr(row, 'next_time'), getattr(row, 'location').split('-')[1]])
            schedule_plot_df = pd.DataFrame(schedule_plot_list, columns=['time', 'stop_id'])
            schedule_plot_df = pd.merge(schedule_plot_df, stations[['stop_id', 'distance']], how='left', on='stop_id')
            if i == 0:
                ax.plot(schedule_plot_df['time'], schedule_plot_df['distance'], '-*', lw=1, ms=3, c='C0', label='Train trajectories')
            else:
                ax.plot(schedule_plot_df['time'], schedule_plot_df['distance'], '-*', lw=1, ms=3, c='C0')
            i += 1

        plt.legend(loc=[0.01, 0.85], fontsize=12, ncol=2)
        plt.tight_layout()
        plt.grid(ls=':')
        # plt.savefig('../uregina/figs/trace_plot_all_trains.png', dpi=200)
    
    def schedule_and_network_from_gtfs(self, stop_times_file, trips_file, stops_file, service_id):
        ### read GTFS files
        stop_times_table = pd.read_csv(stop_times_file)
        trips_table = pd.read_csv(trips_file)
        stops_table = pd.read_csv(stops_file)
        
        ### check format
        stops_table = stops_table.drop_duplicates(subset=['stop_id'])
        
        ### merge the tables
        schedule_table = stop_times_table[['trip_id', 'arrival_time', 'departure_time', 'stop_id', 'shape_dist_traveled']]
        ### assign a route code to individual trains
        trips_table = trips_table[trips_table['service_id']==service_id]
        trips_table['route_id'] = trips_table.apply(lambda x: x['route_id'].split('-')[1]+x['trip_id'][-1], axis=1)
        schedule_table = pd.merge(schedule_table, trips_table[['trip_id', 'route_id']],
                                   how='right', on='trip_id')
        ### assign locations to individual stations
        schedule_table = pd.merge(schedule_table, 
                                    stops_table[['stop_id', 'stop_name', 'stop_lon', 'stop_lat']], how='left', on='stop_id')
        ### assign a route-stop code to individual stops
        schedule_table['route_stop_id'] = schedule_table.apply(lambda x:
                                                               '{}-{}'.format(x['route_id'], x['stop_name']), axis=1)
        
        ### shift line for better plotting
        route_seq_dict = dict()
        seq_id = 0
        for route_id, _ in schedule_table.sort_values(by='route_id', ascending=True).groupby('route_id'):
            route_seq_dict[route_id] = seq_id
            seq_id += 1
        schedule_table = gpd.GeoDataFrame(schedule_table, crs=project_crs, 
                                           geometry=[Point(xy) for xy in zip(schedule_table.stop_lon, 
                                                                             schedule_table.stop_lat)])
        if project_crs is not None:
            schedule_table = schedule_table.to_crs(3857)
        ### calculate shift factor
        minx, miny, maxx, maxy = schedule_table.total_bounds
        shift_factor = (maxx - minx)/10000
        schedule_table['stop_x'] = schedule_table.geometry.x + shift_factor*schedule_table['route_id'].map(route_seq_dict)
        schedule_table['stop_y'] = schedule_table.geometry.y + shift_factor*schedule_table['route_id'].map(route_seq_dict)
        schedule_table['geometry'] = [Point(xy) for xy in zip(schedule_table.stop_x, schedule_table.stop_y)]
        if project_crs is not None:
            schedule_table = schedule_table.to_crs(4326)
        schedule_table['stop_lon'] = schedule_table.geometry.x
        schedule_table['stop_lat'] = schedule_table.geometry.y
        
        ### convert arrival and departure time to seconds since midnight
        schedule_table['arrival_time'] = schedule_table['arrival_time'].apply(
            lambda x: 3600*int(x.split(':')[0]) + 60*int(x.split(':')[1]) +
            int(x.split(':')[2]))
        schedule_table['departure_time'] = schedule_table['departure_time'].apply(
            lambda x: 3600*int(x.split(':')[0]) + 60*int(x.split(':')[1]) +
            int(x.split(':')[2]))
        ### add 30 seconds dwell time at stop if train arrival time = train departure time in GTFS
        schedule_table['departure_time'] = np.where(schedule_table['arrival_time']==schedule_table['departure_time'],
                                                schedule_table['departure_time']+30, schedule_table['departure_time'])
        
        ### link to next stops
        schedule_table = schedule_table.sort_values(by=['trip_id', 'arrival_time'], ascending=True)
        schedule_table['next_route_stop_id'] = schedule_table['route_stop_id'].shift(-1)
        schedule_table['next_stop_lon'] = schedule_table['stop_lon'].shift(-1)
        schedule_table['next_stop_lat'] = schedule_table['stop_lat'].shift(-1)
        schedule_table['next_trip_id'] = schedule_table['trip_id'].shift(-1)
        schedule_table['next_arrival_time'] = schedule_table['arrival_time'].shift(-1)
        schedule_table['next_shape_dist_traveled'] = schedule_table['shape_dist_traveled'].shift(-1)
        schedule_table = schedule_table[schedule_table['trip_id']==schedule_table['next_trip_id']]
        
        ### create schedule and network
        self.add_schedule(schedule_table)
        all_nodes, all_links = self.add_network(schedule_table)
        return all_nodes, all_links