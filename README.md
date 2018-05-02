# sshexpect

This project provides an FSM model base on pexcept to run ssh commands on remote host.

"Action" is the core unit of the FSM model. Now there are 4 types of actions supported:
- command, which will send command to remote host, followed by '\n'.
- operate, which will send a character to remote host.
- end, which is an indicator of success.
- exception, which will raise a pre-define exception.

Each action is a "state" of FSM. The FSM state will transfer by command and its output from remote host.
Following is an example of running privilege command.

![fsm.jpg](http://o7gg8x7fi.bkt.clouddn.com/fsm.jpg)

**State 1.** This state will send command to remote host, when its expect string found in output, it will transfer to
  - State 2, if remote host indicates an password needed
  - State 3, if remote host indicates the output is long and more page is coming.
  - State 4, if remote host indicates a shell prompt.

**State 2.** This state will send password to remote host, and will transfer to
  - State 3, if the password is correct and remote host indicates the output is long and more page is coming.
  - State 4, if the password is correct and remote host indicates a shell prompt.
  - State 5, if the password is wrong.

**State 3.** This state will send a character (generally it is "ANY key") to indicate remote host to print next page, and will transfer to
  - State 3 it self, if there are still more page left.
  - State 4, if all page has been printed and remote host indicates a shell prompt.

**State 4.** This state represents an successful FSM procedure.

**State 5.** This state represents an failed FSM procedure and the reason can be included in the exception raised.

Following is the code to represent this FSM:

``` python
cmd_action = Action("command", command)
succ_action = Action("end")
pass_action = Action("command", password)
failed_action = Action("exception", AuthenticationFailed())
continue_action = Action("operate", " ")
cmd_action.add_next_action(shell_prompt,  succ_action)                # Success directly
cmd_action.add_next_action('.+assword:', pass_action)                 # Need password
cmd_action.add_next_action('--More--\(\d+%\)', continue_action)       # Long output
pass_action.add_next_action(shell_prompt, succ_action)                # Success directly
pass_action.add_next_action("Authentication failure", failed_action)  # Wrong password
pass_action.add_next_action('--More--\(\d+%\)', continue_action)      # Long output
continue_action.add_next_action(shell_prompt, succ_action)
continue_action.add_next_action('--More--\(\d+%\)', continue_action)
```
