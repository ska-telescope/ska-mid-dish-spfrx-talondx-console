#!/bin/bash
rm -f $3; touch $3
kubectl get services -n $1 | while read -r line;
do
    svc_split=($line)
    if [ "${svc_split[1]}" = "LoadBalancer" ]; then
        host_name="${svc_split[0]%"-external"}.$1.svc.$2"
        echo "--add-host=$host_name:${svc_split[3]}" >> $3
    fi
done
