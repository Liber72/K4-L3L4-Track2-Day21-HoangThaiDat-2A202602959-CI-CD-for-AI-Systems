#!/usr/bin/env bash
# Allow this runner to deploy, then revoke only the rule created by this run.
set -euo pipefail

mode="${1:?Usage: runner_ssh.sh open|close}"
: "${EC2_SECURITY_GROUP_ID:?Set the EC2_SECURITY_GROUP_ID repository variable}"
: "${RUNNER_TEMP:?RUNNER_TEMP is required}"
: "${GITHUB_RUN_ID:?GITHUB_RUN_ID is required}"
: "${GITHUB_RUN_ATTEMPT:?GITHUB_RUN_ATTEMPT is required}"
state_file="$RUNNER_TEMP/income-ssh-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT.json"
export AWS_PAGER=""

case "$mode" in
  open)
    runner_ip="$(curl --ipv4 --fail --silent --show-error --retry 3 --max-time 10 https://checkip.amazonaws.com)"
    python -c 'import ipaddress, sys; ip = ipaddress.IPv4Address(sys.argv[1]); assert ip.is_global, "Expected a public runner IPv4 address"' "$runner_ip"
    permissions_file="$RUNNER_TEMP/income-ssh-permissions-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT.json"
    python -c 'import json, sys; json.dump([{"IpProtocol":"tcp","FromPort":22,"ToPort":22,"IpRanges":[{"CidrIp":sys.argv[1],"Description":sys.argv[2]}]}],sys.stdout)' \
      "$runner_ip/32" "income-day21-actions-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT" > "$permissions_file"
    aws ec2 authorize-security-group-ingress \
      --group-id "$EC2_SECURITY_GROUP_ID" \
      --ip-permissions "file://$permissions_file" \
      --cli-connect-timeout 10 --cli-read-timeout 30 --output json > "$state_file"
    rule_id="$(python -c 'import json, sys; rule = json.load(open(sys.argv[1]))["SecurityGroupRules"][0]["SecurityGroupRuleId"]; assert rule.startswith("sgr-"), "Invalid rule ID"; print(rule)' "$state_file")"
    echo "Temporary SSH access granted to $runner_ip/32 ($rule_id)."
    ;;
  close)
    if [[ ! -s "$state_file" ]]; then
      echo "No successful SSH grant recorded for this run."
      exit 0
    fi
    rule_id="$(python -c 'import json, sys; rule = json.load(open(sys.argv[1]))["SecurityGroupRules"][0]["SecurityGroupRuleId"]; assert rule.startswith("sgr-"), "Invalid rule ID"; print(rule)' "$state_file")"
    revoke_file="$RUNNER_TEMP/income-ssh-revoke-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT.json"
    aws ec2 revoke-security-group-ingress \
      --group-id "$EC2_SECURITY_GROUP_ID" \
      --security-group-rule-ids "$rule_id" \
      --cli-connect-timeout 10 --cli-read-timeout 30 --output json > "$revoke_file"
    python -c 'import json, sys; assert json.load(open(sys.argv[1]))["Return"] is True, "Rule revoke failed"' "$revoke_file"
    echo "Temporary SSH rule $rule_id revoked."
    ;;
  *)
    echo "Usage: runner_ssh.sh open|close" >&2
    exit 1
    ;;
esac
