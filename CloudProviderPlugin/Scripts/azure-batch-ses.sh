#!/bin/bash
echo "export AZ_BATCH_ACCOUNT_URL=$AZ_BATCH_ACCOUNT_URL" > /etc/profile.d/ses.sh
echo "export AZ_BATCH_SOFTWARE_ENTITLEMENT_TOKEN=$AZ_BATCH_SOFTWARE_ENTITLEMENT_TOKEN" >> /etc/profile.d/ses.sh
systemctl stop deadline10launcher.service
sleep 5
systemctl start deadline10launcher.service
sleep 3600
