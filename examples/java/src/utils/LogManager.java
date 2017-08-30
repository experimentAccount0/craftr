package utils;
import java.util.logging.Logger;

public class LogManager {

  public Logger getLogger(String name) {
    return Logger.getLogger(name);
  }

  public Logger getLogger(Class c) {
    return getLogger(c.getName());
  }

}
