from enum import Enum


class Copy:

    path = "/restconf/operations/copy-config"

    def __init__(self, source, target):
        self.source = source
        self.target = target

    class Endpoint(Enum):
        RUNNING = "running"
        STARTUP = "startup"

    def content(self):
        body = {
            "yuma-netconf:input": {
                "target": {
                    self.target.value: []
                },
                "source": {
                    self.source.value: []
                }
            }
        }

        return body
