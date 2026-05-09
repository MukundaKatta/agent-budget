%global pypi_name agent-budget
%global pypi_module agent_budget

Name:           python-%{pypi_name}
Version:        0.1.0
Release:        1%{?dist}
Summary:        Production retry/budget primitive for LLM and agent calls

License:        Apache-2.0
URL:            https://github.com/MukundaKatta/%{pypi_name}
Source0:        https://github.com/MukundaKatta/%{pypi_name}/releases/download/v%{version}/%{pypi_module}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3dist(uv-build)

%global _description %{expand:
The retry/budget primitive tenacity isn't, with the three things that
matter for production LLM-shaped work: cost cap, structured per-attempt
events, and adversarial-loop detection (closes the retry-amplification
class of bug from Instructor #2056). Zero runtime dependencies; pure
stdlib at runtime.}

%description %_description

%package -n python3-%{pypi_name}
Summary:        %{summary}

%description -n python3-%{pypi_name} %_description

%prep
%autosetup -p1 -n %{pypi_module}-%{version}

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files %{pypi_module}

%check
%pyproject_check_import

%files -n python3-%{pypi_name} -f %{pyproject_files}
%license LICENSE
%doc README.md CHANGELOG.md

%changelog
* Sat May 09 2026 Mukunda Katta <mukunda.vjcs6@gmail.com> - 0.1.0-1
- Initial Fedora packaging
