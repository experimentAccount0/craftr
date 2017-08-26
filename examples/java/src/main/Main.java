package main;
import utils.HelloDelegateInterfaceClass;
import utils.PlatformIndependentHelloDelegateManager;
import utils.LogManager;
import utils.LogManagerFactory;
import java.util.logging.Logger;
import java.util.ArrayList;
import java.util.List;
import java.util.HashMap;
import java.util.Map;

public class Main {
  public static void main(String[] args) {
    LogManager a = LogManagerFactory.createLogManager();
    Logger e = a.getLogger(Main.class);
    e.info("Retrieving HelloDelegateInterfaceClass from PlatformIndependentHelloDelegateManager");
    HelloDelegateInterfaceClass z = PlatformIndependentHelloDelegateManager.getHelloDelegateInterfaceClassImplementation();
    e.info("Calling HelloDelegateInterfaceClass.getHelloStringFromHelloDelegateInterfaceClass()");
    System.out.println(z.getHelloStringFromHelloDelegateInterfaceClass());
  }
}
