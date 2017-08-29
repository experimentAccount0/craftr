
import * from 'craftr/public'


class TestAction(ActionImpl):

  def display(self, full):
    return "TestAction"

  def abort(self):
    pass

  def execute(self):
    pass


class TestTarget(TargetImpl):

  def translate(self):
    self.action(
      TestAction,
      name = 'foo'
    )


test_target = target_factory(TestTarget)

a = test_target(name = 'a')

b = test_target(name = 'b')

c = test_target(
  name = 'c',
  deps = [':a', ':b']
)
