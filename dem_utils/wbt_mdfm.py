import argparse
import os
from pathlib import Path
import subprocess
from subprocess import PIPE

from misc_utils.logging_utils import create_logger


# Params
wbt = 'whitebox_tools.exe'
mdfm = 'MaxDifferenceFromMean'


def run_subprocess(command):
    proc = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
    # proc.wait()
    output, error = proc.communicate()
    logger.debug('Output: {}'.format(output.decode()))
    logger.debug('Err: {}'.format(error.decode()))


# Args
dem = Path(r'V:\pgc\data\scratch\jeff\ms\2020sep17\dems\raw_clip\WV02_20130627_1030010024B36B00_1030010024807800_2m_lsf_seg2_dem_masked_clip.tif')
out_dir = None
out_mag = None
out_scale = None
min_scale = 1
max_scale = 50
step = 5


def wbt_mdfm(dem, out_dir=None, out_mag=None, out_scale=None,
             min_scale=1, max_scale=50, step=5, vw=False,
             dryrun=False):
    logger.info('Setting up whitebox_tool.exe MaximumDifferenceFromMean')
    if not out_mag:
        out_mag = out_dir / '{}_mdfm_mag_{}-{}-{}{}'.format(dem.stem, min_scale,
                                                            max_scale, step, dem.suffix)
    if not out_scale:
        out_scale = out_dir / '{}_mdfm_scl_{}-{}-{}{}'.format(dem.stem, min_scale,
                                                              max_scale, step, dem.suffix)

    logger.info("""
    DEM: {}
    Magnitude: {}
    Scale: {}
    Min_scale: {}
    Max_scale: {}
    Step: {}
    """.format(dem, out_mag, out_scale, min_scale, max_scale, step))

    # Create command string
    cmd = "{} -r={} --dem={} --out_mag={} --out_scale={} " \
          "--min_scale={} --max_scale={} --step={}""".format(wbt, mdfm, dem, out_mag, out_scale,
                                                             min_scale, max_scale, step)
    if vw:
        cmd += ' -v'

    if not dryrun:
        logger.info('Running MaximumDifferenceFromMean...')
        logger.debug(cmd)
        run_subprocess(cmd)

    logger.info('Done')


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Wrapper for Whitebox Tools MaxDifferenceFromMean tool, with'
                                     'automatically generated output names based on input parameters.')
    parser.add_argument('-i', '--dem', type=os.path.abspath,
                        help='Path to DEM to process.')
    parser.add_argument('-od', '--out_dir', type=os.path.abspath,
                        help='Directory to write output files to, name will be autogenerated'
                             'from input parameters: '
                             '[dem name]_mdfm_[out file type]_[min]-[max]-[step]')
    parser.add_argument('--out_mag', type=os.path.abspath,
                        help='Path to write magnitude file to.')
    parser.add_argument('--out_scale', type=os.path.abspath,
                        help='Path to write scale file to.')
    parser.add_argument('--min_scale', type=int,
                        help='Minimum search neighbourhood radius in grid cells.')
    parser.add_argument('--max_scale', type=int,
                        help='Maximum search neighbourhood radius in grid cells.')
    parser.add_argument('--step', type=int,
                        help='Step size as any positive non-zero integer.')
    parser.add_argument('--dryrun', action='store_true',
                        help='Print actions without performing.')
    parser.add_argument('-vw', '--verbose_wbt', action='store_true',
                        help='Run tool with verbose flag.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Set logging to DEBUG.')

    args = parser.parse_args()

    if args.verbose:
        log_lvl = 'DEBUG'
    else:
        log_lvl = 'INFO'
    logger = create_logger(__name__, 'sh', log_lvl)

    # Determine out_dir if not provided
    if not args.out_dir:
        out_dir = dem.parent
    else:
        out_dir = Path(args.out_dir)

    # Create log file
    log_file = out_dir / '{}_mdfm_{}-{}-{}.log'.format(dem.stem, min_scale,
                                                       max_scale, step)
    logger = create_logger(__name__, 'fh', 'DEBUG',
                           filename=log_file)

    # Run
    wbt_mdfm(dem=Path(args.dem), out_dir=out_dir,
             out_mag=args.out_mag, out_scale=args.out_scale,
             min_scale=args.min_scale, max_scale=args.max_scale,
             step=args.step, vw=args.verbose_wbt,
             dryrun=args.dryrun)
