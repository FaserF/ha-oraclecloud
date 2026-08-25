from logging import Logger, getLogger

DOMAIN = "oraclecloud"

LOGGER: Logger = getLogger(DOMAIN)

CONF_TENANCY = "tenancy"
CONF_USER = "user"
CONF_FINGERPRINT = "fingerprint"
CONF_REGION = "region"
CONF_KEY_CONTENT = "key_content"

CONF_COMPARTMENT = "compartment"
CONF_INSTANCE_ID = "instance_id"

ATTR_OCID = "ocid"
ATTR_REGION = "region"
ATTR_SHAPE = "shape"
ATTR_AVAILABILITY_DOMAIN = "availability_domain"
ATTR_PUBLIC_IP = "public_ip"
ATTR_OS = "os"
ATTR_OS_VERSION = "os_version"

REQUIRED_OCI_VERSION = "2.181.0.post3"
REQUIRED_OCI_GIT_REF = "git+https://github.com/FaserF/oci-python-sdk.git@75b7f381f8885a967df461ebaf5396981e6a1e73#oci"
