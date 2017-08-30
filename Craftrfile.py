
import * from 'craftr'
import actions from 'craftr/actions'


@target_factory
class hello(TargetImpl):

  def translate(self):
    self.action(
      actions.Commands,
      name = 'cmd',
      commands = [['echo', 'Hello, World!'], ['sleep', '1']]
    )


a = hello(name = 'a')
b = hello(name = 'b')
c = hello(
  name = 'c',
  deps = [':a'],
  visible_deps = [':b']
)
