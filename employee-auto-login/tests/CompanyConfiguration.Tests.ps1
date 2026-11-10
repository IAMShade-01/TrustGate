# CompanyConfiguration.Tests.ps1

Describe 'CompanyConfiguration Module Tests' {
    Before {
        # Import the module to be tested
        Import-Module -Name '../src/modules/CompanyConfiguration.psm1'
    }

    It 'Should load company configuration correctly' {
        $config = Get-CompanyConfiguration -Path '../config/company.example.json'
        $config | Should -Not -BeNullOrEmpty
        $config | Should -HaveProperty 'ApiEndpoint'
        $config | Should -HaveProperty 'CredentialStorage'
    }

    It 'Should return default configuration if file does not exist' {
        $config = Get-CompanyConfiguration -Path '../config/nonexistent.json'
        $config | Should -Be 'DefaultConfiguration'
    }

    It 'Should validate required fields in configuration' {
        $config = Get-CompanyConfiguration -Path '../config/company.example.json'
        $isValid = Validate-CompanyConfiguration -Config $config
        $isValid | Should -Be $true
    }

    After {
        # Cleanup if necessary
        Remove-Module CompanyConfiguration
    }
}