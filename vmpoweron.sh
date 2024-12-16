term="fa2024"

# get a username and password
echo -n "Username: "
read username

echo -n "Password: "
read -s password
echo

bundle=$(echo -n $username:$password | base64)

myvm=$(curl "https://courses.grainger.illinois.edu/cs340/$term/secure/myvm.php" -u "$username:$password" --ntlm)
resp=$(curl -X POST "https://vc.cs.illinois.edu/rest/com/vmware/cis/session" -u "$username:$password" --basic)
err=$(echo $resp | jq ".value?.error_type?")
if [ -n "$err" ] && [ "$err" != "null" ]
then
    echo "Authorization error $err" >&2
    exit 1
fi
key=$(echo $resp | jq -r .value)

stats=$(curl --header "vmware-api-session-id: $key" "https://vc.cs.illinois.edu/rest/vcenter/vm?filter.names=$myvm")

echo $stats

state=$(jq -r .value[0].power_state <<<"$stats")
if [ "$state" = "POWERED_ON" ]
then
    echo "$myvm is already on"
    exit 0
fi

vmid=$(jq -r .value[0].vm <<<"$stats")
curl -X POST --header "vmware-api-session-id: $key" "https://vc.cs.illinois.edu/rest/vcenter/vm/$vmid/power/start"
