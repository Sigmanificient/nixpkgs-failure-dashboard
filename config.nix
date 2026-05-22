{
  config = {
    allowAliases = false;
    allowUnfree = true;
    recursionMode = "hydra";
          
    # Theese don't get build by hydra,
    # but it would still be nice to know if they are still building
    android_sdk.accept_license = true;
    dyalog.acceptLicense = true;
    input-fonts.acceptLicense = true;
    joypixels.acceptLicense = true;
    nvidia.acceptLicense = true;
    sc2-headless.accept_license = true;
    segger-jlink.acceptLicense = true;
    xxe-pe.acceptLicense = true;
    microsoftVisualStudioLicenseAccepted = true;
    
    # We build some of these in Hydra.
    allowInsecurePredicate = pkg: true;
  };
}
