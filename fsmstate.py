#!/usr/bin/python
#coding=utf8

import pexpect
import common

class FSMState:

    def __init__(self, state_type, action = None, output_on = True):
        self.state_type = state_type
        self.expects = []
        self.nexts  = []
        self.output_on = output_on
        if state_type == 'command' or state_type == 'operate':
            self.command = action
        if state_type == 'exception':
            self.exception = action
        if state_type == 'end':
            self.end_callback = action

    def add_next_state(self, expect_str, state):
        self.expects.append(expect_str)
        self.nexts.append(state)

    def start(self, p_expect, timeout=10):
        current = self
        output = ''
        while True:
            if current.state_type in ["command", "operate"] :
                p_expect.sendline(current.command)
                common.debug("Send: %s" % (current.command))
                if current.state_type == "command":
                    p_expect.readline()
                try:
                    i = p_expect.expect(current.expects, timeout)
                    if current.output_on:
                        output += p_expect.before
                    current = current.nexts[i]
                except pexpect.TIMEOUT:
                    raise common.Timeout('Command timeout!')
                except pexpect.EOF:
                    return p_expect.exitstatus
            elif current.state_type == "exception":
                raise current.exception
            elif current.state_type == "end":
                if current.end_callback:
                    current.end_callback()
                break
        return output
