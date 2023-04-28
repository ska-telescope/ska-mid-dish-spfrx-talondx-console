#!/bin/bash

base_dir=$1
if [[ -z $base_dir ]]; then echo "No base directory provided"; exit 5;fi
if [[ ! -d $base_dir ]]; then echo "Base directory does not exist"; exit 20;fi
date_dir=$(date +%Y-%m-%d)
time_dir=$(date +%H-%M-%S)
final_dir=$base_dir/$date_dir/$time_dir
echo "$final_dir" > $2
mkdir -p $final_dir
