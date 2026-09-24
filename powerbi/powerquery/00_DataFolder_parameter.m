// DataFolder - Power Query parameter
// Set this to the folder that holds the Step 11 CSV extracts, e.g.
//   "C:\\projects\\customer-revenue-intelligence\\powerbi\\data\\"
// Keep the trailing backslash. Every query reads from this one parameter, so the
// report is repointed at a new machine by changing this single value.
"C:\projects\customer-revenue-intelligence\powerbi\data\" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]
