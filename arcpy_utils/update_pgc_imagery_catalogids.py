import argparse
import datetime
import logging
import os

import arcpy

# args
dryrun = True
verbose = True
logdir = r'C:\temp\log'


def get_platform_code(platform):
    platform_code = {
                    'QB02': '101',
                    'WV01': '102',
                    'WV02': '103',
                    'WV03': '104',
                    # 'WV03-SWIR': '104A',
                    'GE01': '105',
                    'IK01': '106'
                    }

    return platform_code[platform]


def cid_from_sid(sid):
    """Parses a catalog_id from a scene_id"""
    try:
        cid = sid.split('_')[2]
    except IndexError:
        # TODO: Catch/log this?
        cid = None

    return cid


def get_unique_ids(table, field, where=None, clean_fxn=None):
    """
    Loads unique IDs from the given field in the given table, optionally
    with the provided where clause, optionally applying a function to
    each id before returning.

    Parameters:
    table: os.path.abspath
        The path to the table to parse.
    field: str
        The field in table to parse.
    where: str
        SQL WHERE clause to subset table.
    clean_fxn: function
        Function to apply to each ID before returning.

    Returns:
    set: unique values from the given field
    """
    logger.debug('Loading {} IDs WHERE {}'.format(os.path.basename(table), where))

    unique_ids = set()
    for row in arcpy.da.SearchCursor(in_table=table, field_names=[field], where_clause=where):
        the_id = row[0]
        if clean_fxn:
            the_id = clean_fxn(the_id)
        unique_ids.add(the_id)

    logger.debug('Unique IDs: {:,}'.format(len(unique_ids)))

    return unique_ids


def compare_tables(tbl_a, tbl_b,
                   field_a, field_b,
                   where_a=None, where_b=None,
                   clean_fxn_a=None, clean_fxn_b=None):
    """
    Compares the values in two tables, return two sets, the values in
    table A not in table B, and the values in table B not in table A,
    using supplied where clauses to limit records and functions to
    modify values.

    Parameters:
    tbl_a: os.path.abspath
        The path to the first table to parse.
    tbl_b: os.path.abspath
        The path to the second table to parse.
    field_a: str
        The field in table A to parse.
    tbl_b: str
        The field in table B to parse.
    where_a: str
        SQL where clause to subset table A.
    where_b: str
        SQL where clause to subset table B.
    clean_fxn_a: function
        The function to apply to each value in table A before comparing.
    clean_fxn_b: function
        The function to apply to each value in table B before comparing.

    Returns:
    tuple: with two sets (missing from table A {b-a}, missing from table B {a-b})
    """
    tbl_a_vals = get_unique_ids(table=tbl_a, field=field_a, where=where_a, clean_fxn=clean_fxn_a)
    tbl_b_vals = get_unique_ids(table=tbl_b, field=field_b, where=where_b, clean_fxn=clean_fxn_b)
    # Exists in B but not A
    missing_from_a = tbl_b_vals - tbl_a_vals
    # Exists in A but not B
    missing_from_b = tbl_a_vals - tbl_b_vals

    return (missing_from_a, missing_from_b)


def update_table(sde, table, catid_fld, sensor_fld, new_ids, missing_catids, dryrun=False):
    """Updates the given table by adding the ids in new ids and removing the
    ids in missing ids (if any passed).

    Parameters:
    sde: os.path.abspath
        Path to the sde connection file to the database containing table to modify.
    table: os.path.abspath
        Path to the table to update
    catid_fld: str
        Name of the catalog_id field to update.
    sensor_fld: str
        Name of the sensor field to update.
    new_ids: dict
        {sensor: set of ids to add to table}
    missing_catids: set
        ids to remove from table

    Returns:
    None
    """
    # For logging only
    table_name = os.path.basename(table)

    # Start editing
    edit = arcpy.da.Editor(sde)
    edit.startEditing(False, True)
    edit.startOperation()

    # Add new IDs
    logger.info('Appending new catalog IDs to: {}'.format(table_name))
    with arcpy.da.InsertCursor(table, [catid_fld, sensor_fld]) as icur:
        i = 0
        for platform, cids in new_ids.items():
            for cid in cids:
                # TODO: Do we want to log each ID written or deleted?
                # logger.debug('Appending {}: {} - {}'.format(i, cid, platform))
                if not dryrun:
                    icur.insertRow([cid, platform])
                i += 1
    del icur
    edit.stopOperation()
    logger.info('Records added to {}: {:,}'.format(table_name, i))

    if missing_catids:
        # Delete missing
        edit.startOperation()
        logger.info('Deleting missing catalog IDs from: {}'.format(table_name))
        with arcpy.da.UpdateCursor(table, [catid_fld]) as ucur:
            i = 0
            for row in ucur:
                catid = row[0]
                if catid in missing_catids:
                    # logger.debug('Deleting {}'.format(catid))
                    if not dryrun:
                        ucur.deleteRow()
                    i += 1
        del ucur
        edit.stopOperation()
        logger.info('Records deleted from {}: {}'.format(table_name, i))

    edit.stopEditing(True)

    logger.debug('Getting updated count for {}'.format(table_name))
    table_catid_count = int(arcpy.GetCount_management(table).getOutput(0))
    logger.info('{} updated count: {:,}'.format(table_name, table_catid_count))


#### Logging setup
logger = logging.getLogger(__name__)
if verbose:
    logging_level = logging.DEBUG
else:
    logging_level = logging.INFO

logger.setLevel(logging_level)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# Stream handler
sh = logging.StreamHandler()
sh.setFormatter(formatter)
logger.addHandler(sh)
# File handler
if not logdir:
    # TODO: Where should logs go?
    logdir = os.path.join(os.path.dirname(__file__), 'logs')
if not os.path.isdir(logdir):
    os.makedirs(logdir)
now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
logfile = os.path.join(logdir, '{}_{}.log'.format(os.path.splitext(os.path.basename('update_test'))[0], now))
fh = logging.FileHandler(logfile)
fh.setLevel(logging_level)
fh.setFormatter(formatter)
logger.addHandler(fh)


#### Paths to sde files and tables
# dgarchive
# TODO: Create this sde file in an accessible location
dgarchive_sde = r'C:\dbconn\sandwich-pool.dgarchive.sde'
canon_catid_table = 'dgarchive.footprint.canon_catalog_ids'
canon_sid_tbl = 'dgarchive.footprint.canon_scene_ids'
canon_catid_table_abs = os.path.join(dgarchive_sde, canon_catid_table)
canon_sid_tbl_abs = os.path.join(dgarchive_sde, canon_sid_tbl)
# danco
# danco_sde = r'C:\dbconn\footprint.sde'
danco_sde = r'\\files.umn.edu\pgc\trident\db\danco\footprint.sde'
danco_catid_table = 'footprint.sde.pgc_imagery_catalogids'
danco_stereo_tbl = 'footprint.sde.pgc_imagery_catalogids_stereo'
danco_catid_table_abs = os.path.join(danco_sde, danco_catid_table)
danco_stereo_tbl_abs = os.path.join(danco_sde, danco_stereo_tbl)

#### Constants
platforms = ['QB02', 'WV01', 'WV02', 'WV03', 'GE01', 'IK01']
catid_fld = 'catalog_id'
sid_fld = 'scene_id'
sensor_fld = 'sensor'
# TODO: What should sensor be for IDs that don't confirm to platform code convention?
other = 'other'  # used as 'sensor' for IDs that don't conform to the platform code


#### Starting table counts
starting_counts = dict()
for tbl in [danco_catid_table_abs, danco_stereo_tbl_abs]:
    tbl_count = int(arcpy.GetCount_management(tbl).getOutput(0))
    logger.info('{} starting count: {:,}'.format(os.path.basename(tbl), tbl_count))
    starting_counts[tbl] = tbl_count
print('\n')

#### Update danco table: pgc_imagery_catalogids
logger.info('Determining required updates for {}...'.format(danco_catid_table))

# Create dict of platform name and associated where clause
platform_wheres = {p: """{} LIKE '{}%'""".format(catid_fld, get_platform_code(p)) for p in platforms}
# Add catch all where clause for IDs that do not conform to naming convention
platform_wheres[other] = ' AND '.join(["({} NOT LIKE '{}%')".format(catid_fld,
                                                                    get_platform_code(p)) for p in platforms])

# Load each platform's IDs for canon_catalog_ids and pgc_imagery_catalogids, find difference
new_catids = dict()
missing_catids = set()
for platform, where in platform_wheres.items():
    logger.info('Parsing {} IDs...'.format(platform))
    # Identify new and missing IDs for platform (returns: b-a, a-b)
    new_platform, missing_platform = compare_tables(tbl_a=danco_catid_table_abs,
                                                    tbl_b=canon_catid_table_abs,
                                                    field_a=catid_fld, field_b=catid_fld,
                                                    where_a=where, where_b=where)
    logger.info('New IDs for {}: {:,}'.format(platform, len(new_platform)))
    logger.info('Missing IDs for {}: {:,}'.format(platform, len(missing_platform)))
    # Capture new and missing IDs
    new_catids[platform] = new_platform
    missing_catids = missing_catids | missing_platform

    del new_platform, missing_platform
print('\n')

# Perform updates: pgc_catalogids
logger.info('Making updates to {}'.format(danco_catid_table))
update_table(danco_sde, danco_catid_table_abs,
             catid_fld=catid_fld, sensor_fld=sensor_fld,
             new_ids=new_catids, missing_catids=missing_catids,
             dryrun=dryrun)

del new_catids, missing_catids
print('\n\n')


#### Update danco table: pgc_imagery_ids_stereo
logger.info('Determining required updates for {}'.format(danco_stereo_tbl))
# Add P1BS to all canon_scene_id where clauses
canon_wheres = {p: """{0} LIKE '{1}%' AND {0} LIKE '%P1BS%'""".format(sid_fld, p) for p in platforms}
# Separate catch all where clause to use platform rather than code
canon_where_other = ' AND '.join(["({} NOT LIKE '{}%')".format(sid_fld, p) for p in platforms])
canon_where_other += "  AND ({} LIKE '%P1BS%')".format(sid_fld)

new_stereo_catids = dict()
missing_stereo_catids = set()
for platform, where in platform_wheres.items():
    logger.info('Parsing {} IDs...'.format(platform))
    # Where clauses
    if platform == other:
        canon_where = canon_where_other
    else:
        canon_where = canon_wheres[platform]
    # Identify new and missing IDs for platform
    new_platform, missing_platform = compare_tables(tbl_a=danco_stereo_tbl_abs,
                                                    tbl_b=canon_sid_tbl_abs,
                                                    field_a=catid_fld,
                                                    field_b=sid_fld,
                                                    where_a=where,
                                                    where_b=canon_where,
                                                    clean_fxn_a=None,
                                                    clean_fxn_b=cid_from_sid)
    logger.info('New IDs for {}: {:,}'.format(platform, len(new_platform)))
    logger.info('Missing IDs for {}: {:,}'.format(platform, len(missing_platform)))
    # Capture new and missing IDs
    new_stereo_catids[platform] = new_platform
    missing_stereo_catids = missing_stereo_catids | missing_platform

    del new_platform, missing_platform
print('\n')

# Perform updates: pgc_imagery_catalogids_stereo
update_table(danco_sde, danco_stereo_tbl_abs,
             catid_fld=catid_fld, sensor_fld=sensor_fld,
             new_ids=new_stereo_catids, missing_catids=missing_stereo_catids,
             dryrun=dryrun)
del new_stereo_catids, missing_stereo_catids
print('\n\n')

# Compare starting counts and ending counts
for tbl in [danco_catid_table_abs, danco_stereo_tbl_abs]:
    tbl_name = os.path.basename(tbl)
    logger.info('{} starting count: {:,}'.format(tbl_name, starting_counts[tbl]))
    ending_count = int(arcpy.GetCount_management(tbl).getOutput(0))
    logger.info('{} ending count:   {:,}'.format(tbl_name, ending_count))
    logger.info('{} change:         {:,}'.format(tbl_name, ending_count-starting_counts[tbl]))
    print('\n')

logger.info('Done.')
