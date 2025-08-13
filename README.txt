ECC Route Fix — Portfolio (properties/units/leases)

What this does
--------------
Updates the three Azure Functions so they respond on:
  /api/portfolio/properties
  /api/portfolio/units
  /api/portfolio/leases

Upload these three folders to your repo ROOT (same level as host.json).
If GitHub prompts to replace function.json, click Replace.
Then run your Deploy workflow.

Test:
  https://empirecommandcenter-altus.azurewebsites.net/api/portfolio/properties?limit=5
  https://empirecommandcenter-altus.azurewebsites.net/api/portfolio/units?limit=5
  https://empirecommandcenter-altus.azurewebsites.net/api/portfolio/leases?limit=5
