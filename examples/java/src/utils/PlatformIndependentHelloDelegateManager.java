package utils;

public class PlatformIndependentHelloDelegateManager {

  public static HelloDelegateInterfaceClass getHelloDelegateInterfaceClassImplementation() {
    return new HelloDelegateInterfaceClass() {
      public String getHelloStringFromHelloDelegateInterfaceClass() {
        return "Hello, World!";
      }
    };
  }

}
