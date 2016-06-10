#!/bin/sh

echo "{
	\"id\": \"policy1\",
	\"description\": \"My access control policy\",
	\"rule_combining\": \"permit_overrides\",
	\"target\": {
		\"subject\": {
			\"actor_signer\": \".*\"
		},
		\"action\": {
			\"requires\": [\"calvinsys.native.*\", \"calvinsys.network.httpclienthandler\", \"calvinsys.attribute.*\", \"runtime\"]
		},
		\"resource\": {
			\"node_name.name\": \"secret_room\"
		}
	},
	\"rules\": [
		{
			\"id\": \"policy1_rule1\",
			\"description\": \"Rule description\",
			\"effect\": \"permit\",
			\"condition\": {
				\"function\": \"or\",
				\"attributes\": [
					{
						\"function\": \"equal\",
						\"attributes\": [\"attr:subject:group\", \"Security\"]
					},
					{
						\"function\": \"equal\",
						\"attributes\": [\"attr:subject:position\", \"Manager\"]
					}
				]
			},
			\"obligations\": [
				{
					\"id\": \"time_range\",
					\"attributes\": {
						\"start_time\": \"$1\",
						\"end_time\": \"$2\"
					}
				}
			]
		}
	]
}" > ~/.calvin/security/policies/policy1.json
