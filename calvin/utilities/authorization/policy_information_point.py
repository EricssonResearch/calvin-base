# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime

class PolicyInformationPoint(object):
    attributes = {
        "environment": {
            "current_date": datetime.now().strftime('%Y-%m-%d'),
            "current_time": datetime.now().strftime('%H:%M')
            # "test_attribute": my_function
        }
    }

    def get_attribute_value(self, attribute_type, attribute):
    	"""Return the specified attribute if it exists in attributes dictionary"""
        return PolicyInformationPoint.attributes[attribute_type][attribute]