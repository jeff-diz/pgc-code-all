# -*- coding: utf-8 -*-
"""
Created on Tue Jun 18 12:52:32 2019

@author: disbr007
"""

from id_parse_utils import compare_ids
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("list_1", type=str, help="Path to text file of first list of ids.")
    parser.add_argument("list_2", type=str, help="Path to text file of first list of ids.")
    
    args = parser.parse_args()
    
    ids1, ids2, com = compare_ids(args.list_1, args.list_2, write_path=True)
    
    print('Unique to list 1: {}'.format(len(ids1)))
    print('Unique to list 2: {}'.format(len(ids2)))
    print('Common: {}'.format(len(com)))
    
if __name__ == "__main__":
    main()