+++
title = "Null"
+++

```python
import {null} from 'craftr/actions'
```

The null action does nothing, really. Targets that do not actually need to
produce an action should generate a null action instead, as it is necessary
to keep the dependency information of the target in the action graph.

__Example__

```python
class JavaPrebuilt(craftr.AnnotatedTarget):

  binary_jar: str

  def translate(self):
    actions.null(self, name='null', deps=self.deps())
```
